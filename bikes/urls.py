from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logins/', views.user_logins, name='logins'),
    path('logout/', views.user_logout, name='logout'),
    path('', views.bike_list, name='bike_list'),
    path('booking/', views.booking, name='booking'),
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:bike_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:bike_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('confirm_booking/', views.confirm_booking, name='confirm_booking'),
    path('booking-success/', views.bookings_success, name='booking_success'),
    path('my-bookings/', views.user_bookings, name='user_bookings'),
    path('confirm_payment/<int:booking_id>/', views.confirm_payment, name='confirm_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
    path('authorize-payment/<str:order_id>/', views.authorize_payment, name='authorize_payment'),
    path('profile/', views.user_profile, name='user_profile'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_manage_bikes/', views.manage_bikes, name='manage_bikes'),
    path('manage_bikes/', views.manage_bikes, name='manage_bikes'),
    path('update_bike/<int:bike_id>/',views.update_bike, name='update_bike'),
    path('delete_bike/<int:bike_id>/',views.delete_bike, name='delete_bike'),
    path('manage_bookings/', views.manage_bookings, name='manage_bookings'),
    path('confirm_booking/<int:booking_id>/', views.confirm_bookings, name='confirm_booking'),
    path('cancel_booking/<int:booking_id>/', views.cancel_bookings, name='cancel_booking'),
    path('return_booking/<int:booking_id>/', views.return_bookings, name='return_booking'),
    path('add_bike/',views.add_bike, name='add_bike'),





]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
