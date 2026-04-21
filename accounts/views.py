from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.http import HttpResponseForbidden

from .models import User
from .models_invite import Invitation
from .forms import LoginForm, InviteRegistrationForm, SendInviteForm, BulkInviteForm, UserProfileForm


# ── Login / Logout ─────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'dashboard:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('/')


# ── Invite-based Registration ──────────────────────────────────────────────────

def register_via_invite(request, token):
    """
    Public view — no login required.
    User lands here from their invite email link.
    """
    invitation = get_object_or_404(Invitation, token=token)

    # Check invite is still usable
    if not invitation.is_valid:
        if invitation.is_expired:
            invitation.mark_expired()
            return render(request, 'accounts/invite_invalid.html', {
                'reason': 'expired',
                'invitation': invitation,
            })
        return render(request, 'accounts/invite_invalid.html', {
            'reason': invitation.status,  # 'accepted' or 'revoked'
            'invitation': invitation,
        })

    if request.method == 'POST':
        form = InviteRegistrationForm(request.POST, invitation=invitation)
        if form.is_valid():
            user = form.save()
            invitation.accept(user)

            # Log the user in immediately
            login(request, user)
            messages.success(
                request,
                f'Welcome to the platform, {user.first_name}! Your account has been created.'
            )
            return redirect('dashboard:home')
    else:
        form = InviteRegistrationForm(invitation=invitation)

    return render(request, 'accounts/register_invite.html', {
        'form': form,
        'invitation': invitation,
    })


# ── Send Invites (Admin / Teacher) ─────────────────────────────────────────────

def _can_send_invites(user):
    """Only admins and teachers can send invites."""
    return user.is_school_admin or user.is_teacher


@login_required
def send_invite(request):
    if not _can_send_invites(request.user):
        return HttpResponseForbidden('You do not have permission to send invitations.')

    if request.method == 'POST':
        form = SendInviteForm(request.POST)
        if form.is_valid():
            invite = Invitation.objects.create(
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data.get('first_name', ''),
                last_name=form.cleaned_data.get('last_name', ''),
                role=form.cleaned_data['role'],
                personal_message=form.cleaned_data.get('personal_message', ''),
                invited_by=request.user,
            )
            _send_invite_email(invite, request)
            messages.success(request, f'Invitation sent to {invite.email}.')
            return redirect('accounts:invite_list')
    else:
        form = SendInviteForm()

    return render(request, 'accounts/send_invite.html', {'form': form})


@login_required
def bulk_invite(request):
    if not _can_send_invites(request.user):
        return HttpResponseForbidden('You do not have permission to send invitations.')

    if request.method == 'POST':
        form = BulkInviteForm(request.POST)
        if form.is_valid():
            emails = form.cleaned_data['emails']
            role = form.cleaned_data['role']
            sent, skipped = 0, 0

            for email in emails:
                # Skip if pending invite or existing user
                if (Invitation.objects.filter(email=email, status='pending').exists()
                        or User.objects.filter(email=email).exists()):
                    skipped += 1
                    continue

                invite = Invitation.objects.create(
                    email=email,
                    role=role,
                    invited_by=request.user,
                )
                _send_invite_email(invite, request)
                sent += 1

            messages.success(request, f'{sent} invitation(s) sent. {skipped} skipped (already exist).')
            return redirect('accounts:invite_list')
    else:
        form = BulkInviteForm()

    return render(request, 'accounts/bulk_invite.html', {'form': form})


@login_required
def resend_invite(request, pk):
    if not _can_send_invites(request.user):
        return HttpResponseForbidden()

    invite = get_object_or_404(Invitation, pk=pk)

    if invite.status not in ('pending', 'expired'):
        messages.error(request, 'This invitation cannot be resent.')
        return redirect('accounts:invite_list')

    # Reset token and expiry
    import uuid
    from datetime import timedelta
    invite.token = uuid.uuid4()
    invite.expires_at = timezone.now() + timedelta(hours=72)
    invite.status = 'pending'
    invite.save()

    _send_invite_email(invite, request)
    messages.success(request, f'Invitation resent to {invite.email}.')
    return redirect('accounts:invite_list')


@login_required
def revoke_invite(request, pk):
    if not _can_send_invites(request.user):
        return HttpResponseForbidden()

    invite = get_object_or_404(Invitation, pk=pk)
    invite.revoke()
    messages.success(request, f'Invitation to {invite.email} has been revoked.')
    return redirect('accounts:invite_list')


# ── Invite List (Admin dashboard) ─────────────────────────────────────────────

class InviteListView(LoginRequiredMixin, ListView):
    model = Invitation
    template_name = 'accounts/invite_list.html'
    context_object_name = 'invitations'
    paginate_by = 25

    def get_queryset(self):
        if not _can_send_invites(self.request.user):
            return Invitation.objects.none()
        # Admins see all; teachers see only their own
        if self.request.user.is_school_admin:
            qs = Invitation.objects.all()
        else:
            qs = Invitation.objects.filter(invited_by=self.request.user)
        return qs.select_related('invited_by', 'accepted_by').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['stats'] = {
            'pending':  qs.filter(status='pending').count(),
            'accepted': qs.filter(status='accepted').count(),
            'expired':  qs.filter(status='expired').count(),
            'revoked':  qs.filter(status='revoked').count(),
        }
        return context


# ── Email helper ───────────────────────────────────────────────────────────────

def _send_invite_email(invitation, request):
    """Send the invite email with a one-click registration link."""
    register_url = request.build_absolute_uri(
        invitation.get_register_url()
    )

    subject = f"You've been invited to join the platform"
    html_body = render_to_string('accounts/emails/invite_email.html', {
        'invitation': invitation,
        'register_url': register_url,
        'inviter': invitation.invited_by,
        'expiry_hours': 72,
    })
    plain_body = (
        f"Hi {invitation.first_name or 'there'},\n\n"
        f"You've been invited to join as a {invitation.get_role_display()}.\n\n"
        f"Click here to create your account:\n{register_url}\n\n"
        f"This link expires in 72 hours.\n\n"
        f"If you did not expect this invitation, you can ignore this email."
    )

    send_mail(
        subject=subject,
        message=plain_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
        html_message=html_body,
        fail_silently=False,
    )


# ── Profile ────────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs