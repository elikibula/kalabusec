from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # ── Auth ─────────────────────────────────────────────────
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Registration ─────────────────────────────────────────
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/<uuid:token>/', views.register_via_invite, name='register_invite'),

    # ── Profile ──────────────────────────────────────────────
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),

    # ── Invitations ──────────────────────────────────────────
    path('invites/', views.InviteListView.as_view(), name='invite_list'),
    path('invites/send/', views.send_invite, name='send_invite'),
    path('invites/bulk/', views.bulk_invite, name='bulk_invite'),
    path('invites/<int:pk>/resend/', views.resend_invite, name='resend_invite'),
    path('invites/<int:pk>/revoke/', views.revoke_invite, name='revoke_invite'),
]
