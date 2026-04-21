from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Invite-based registration (replaces open /register/) ──────────────────
  
    path('register/<uuid:token>/', views.register_via_invite, name='register_invite'),


    # ── Sending invites (admin / teacher only) ────────────────────────────────
    path('invites/',            views.InviteListView.as_view(), name='invite_list'),
    path('invites/send/',       views.send_invite,              name='invite_send'),
    path('invites/bulk/',       views.bulk_invite,              name='invite_bulk'),
    path('invites/<int:pk>/resend/', views.resend_invite,       name='invite_resend'),
    path('invites/<int:pk>/revoke/', views.revoke_invite,       name='invite_revoke'),

    # ── Profile ───────────────────────────────────────────────────────────────
    path('profile/',      views.profile_view,                name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
]



