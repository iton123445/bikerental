from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

from .models import Bike, Booking, Transaction
from .forms import BookingForm, BikeForm
import requests
from django.urls import reverse
from django.conf import settings
import logging
from django.http import JsonResponse,HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

def get_access_token():
    token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {settings.PAYPAL_CLIENT_ID_SECRET_BASE64}'
    }
    data = {
        'grant_type': 'client_credentials'
    }

    response = requests.post(token_url, headers=headers, data=data)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception("Failed to obtain access token")
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful. You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})
def user_logout(request):
    logout(request)
    return redirect('logins') 
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('bike_list')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def user_logins(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Check if the user is staff (admin)
                if user.is_staff:
                    return redirect('admin_dashboard')
                else:
                    # Redirect non-staff users to another page
                    return redirect('bike_list')  # Or any other page you want to redirect non-admin users
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'logins.html', {'form': form})

@login_required
def add_to_cart(request, bike_id):
    if request.user.is_authenticated:
        bike = Bike.objects.get(id=bike_id)
        cart = request.session.get('cart', {})
        cart[bike_id] = cart.get(bike_id, 0) + 1
        request.session['cart'] = cart
        messages.success(request, 'Item added to cart successfully.')
        return redirect('cart')
    else:
        messages.error(request, 'Please login to add items to cart.')
        return redirect('user_logins')
    
def user_profile(request):
    # Retrieve user's booking history
    bookings = Booking.get_user_bookings(request.user)
    return render(request, 'user_profile.html', {'bookings': bookings})

def bike_list(request):
    bikes = Bike.objects.filter(available=True)
    return render(request, 'bike_list.html', {'bikes': bikes})

def booking(request, bike_id):
    bike = Bike.objects.get(id=bike_id)
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            booking = Booking.objects.create(
                bike=bike,
                start_date=start_date,
                end_date=end_date,
                user=request.user,
                status='Pending'
            )
            bike.available = False
            bike.save()
            return redirect('confirm_booking')
    else:
        form = BookingForm()
    return render(request, 'booking.html', {'form': form, 'bike': bike})

def cart(request):
    cart = request.session.get('cart', {})
    bike_ids = list(cart.keys())
    bikes = Bike.objects.filter(id__in=bike_ids)
    
    total_price = sum(bike.price * cart[str(bike.id)] for bike in bikes)
    
    return render(request, 'cart.html', {'bikes': bikes, 'cart': cart, 'total_price': total_price})

@login_required
def add_to_cart(request, bike_id):
    bike = Bike.objects.get(id=bike_id)
    cart = request.session.get('cart', {})
    cart[bike_id] = cart.get(bike_id, 0) + 1
    request.session['cart'] = cart
    return redirect('cart')

def remove_from_cart(request, bike_id):
    cart = request.session.get('cart', {})
    if str(bike_id) in cart:
        del cart[str(bike_id)]
        request.session['cart'] = cart
    return redirect('cart')

def confirm_booking(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            bike_id = form.cleaned_data['bike_id']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Retrieve bike object or return 404 if not found
            bike = get_object_or_404(Bike, id=bike_id)
            
            # Create a new booking with the provided details
            booking = Booking.objects.create(
                bike=bike,
                user=request.user,
                start_date=start_date,
                end_date=end_date,
                status='Pending'
            )
            
            # Remove the booked bike from the cart
            cart = request.session.get('cart', {})
            if str(bike_id) in cart:
                del cart[str(bike_id)]
                request.session['cart'] = cart
            
            # Redirect to payment confirmation page with the booking ID
            return redirect('confirm_payment', booking_id=booking.id)
    else:
        form = BookingForm()

    return render(request, 'confirm_booking.html', {'form': form})

def confirm_payment(request, booking_id):
    # View to handle payment confirmation and redirection to PayPal
    try:
        booking = get_object_or_404(Booking, pk=booking_id)
        bike = booking.bike

        # Calculate total amount based on booking duration and bike price
        if booking.start_date and booking.end_date:
            number_of_days = (booking.end_date - booking.start_date).days   
            total_amount = bike.price * number_of_days
        else:
            total_amount = 0

        # Obtain PayPal access token
        access_token = get_access_token()

        # Set up PayPal API endpoint and headers
        url = 'https://api-m.sandbox.paypal.com/v2/checkout/orders'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        # Set up payload for creating a PayPal order
        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': str(booking.id),
                'amount': {
                    'currency_code': 'USD',
                    'value': f'{total_amount:.2f}'
                }
            }],
            'application_context': {
                'return_url': request.build_absolute_uri(reverse('payment_success')),
                'cancel_url': request.build_absolute_uri(reverse('payment_cancel'))
            }
        }

        # Make a POST request to create the PayPal order
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 201:
            # If order creation is successful, retrieve the approval URL and redirect
            order_data = response.json()
            approval_url = next(link['href'] for link in order_data['links'] if link['rel'] == 'approve')
            return HttpResponseRedirect(approval_url)
        else:
            # If order creation fails, display an error message and redirect to cart
            messages.error(request, f"Failed to create PayPal order: {response.text}")
            return HttpResponseRedirect(reverse('cart'))

    except Exception as e:
        # Handle any exceptions during the payment confirmation process
        messages.error(request, f"Error connecting to PayPal: {str(e)}")
        return HttpResponseRedirect(reverse('cart'))

def confirm_payment_source(order_id, access_token):
    url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    payload = {
        "payment_source": {
            "paypal": {
                "name": {
                    "given_name": "John",
                    "surname": "Doe"
                },
                "email_address": "restaurant_customer1@personal.example.com",
                "experience_context": {
                    "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                    "brand_name": "EXAMPLE INC",
                    "locale": "en-US",
                    "landing_page": "LOGIN",
                    "shipping_preference": "SET_PROVIDED_ADDRESS",
                    "user_action": "PAY_NOW",
                    "return_url": "https://example.com/returnUrl",
                    "cancel_url": "https://example.com/cancelUrl"
                }
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()

        if response.status_code == 200:
            # Payment source confirmed successfully
            return True
        else:
            # Payment source confirmation failed
            return False, response_data.get('message', 'Payment source confirmation failed.')

    except Exception as e:
        # Error connecting to PayPal API
        return False, f"Error connecting to PayPal API: {str(e)}"
    

def authorize_payment(order_id):
    try:
        access_token = get_access_token()

        # Define the endpoint URL for payment authorization
        url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/authorize'

        # Prepare headers for the authorization request
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'PayPal-Request-Id': '{order_id}'  # Example PayPal-Request-Id
        }

        # Send the POST request to authorize payment
        response = requests.post(url, headers=headers)

        if response.status_code == 201:
            # Authorization successful
            return JsonResponse({'message': 'Payment authorized successfully'}, status=201)
        else:
            # Authorization failed
            error_message = response.json().get('message', 'Payment authorization failed')
            return JsonResponse({'error': error_message}, status=response.status_code)

    except Exception as e:
        # Handle exceptions
        return JsonResponse({'error': f"Error authorizing payment: {str(e)}"}, status=500)
    
def get_order_id_from_token(token, access_token):
    try:
        url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{token}'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(url, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            order_id = response_data.get('id')
            return order_id
        else:
            # Handle API error responses
            error_message = response_data.get('message', 'Unknown error')
            raise Exception(f"Error retrieving order ID: {error_message}")

    except Exception as e:
        # Log the error and handle appropriately
        raise Exception(f"Error retrieving order ID: {str(e)}")
def get_booking_id_from_order(order_id):
    try:
        # Retrieve the booking ID associated with the given PayPal order ID
        transaction = Transaction.objects.get(transaction_id=order_id)
        return transaction.booking_id

    except Transaction.DoesNotExist:
        # Handle case where no mapping exists for the provided order ID
        return None

    except Exception as e:
        # Log and handle other exceptions (e.g., database error)
        logger.error(f"Error retrieving booking ID from order ID: {str(e)}")
        return None
def payment_success(request):
    token = request.GET.get('token')
    payer_id = request.GET.get('PayerID')

    if token and payer_id:
        try:
            access_token = get_access_token()
            order_id = get_order_id_from_token(token, access_token)

            if order_id:
                booking_id = get_booking_id_from_order(order_id)  # Retrieve booking_id

                if booking_id:
                    # Retrieve the booking based on booking_id
                    booking = get_object_or_404(Booking, pk=booking_id)

                    # Update booking status to 'Confirmed'
                    booking.status = 'Confirmed'
                    booking.save()

                    # Record transaction in the database (optional)
                    Transaction.objects.create(order_id=order_id, booking=booking, amount=booking.total_amount)

                    messages.success(request, 'Payment successful! Booking is confirmed.')
                else:
                    messages.error(request, 'Booking not found.')
            else:
                messages.error(request, 'Error: Unable to retrieve order ID from PayPal.')

        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")

    return redirect('user_bookings')

def capture_payment(order_id, access_token):
    try:
        url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        payload = {}

        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()

        if response.status_code == 201 and response_data.get('status') == 'COMPLETED':
            print("capture_payment: success")
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error capturing payment: {str(e)}")
        return False

def bookings_success(request):
    return render(request, 'booking_success.html')

def user_bookings(request):
    if request.user.is_authenticated:
        user_bookings = Booking.objects.filter(user=request.user)
        return render(request, 'user_bookings.html', {'user_bookings': user_bookings})
    else:
        print(request.session.get('show_message'))
        request.session['show_message'] = True

        messages.error(request, 'You need to login to view your bookings.')
        return redirect('login')

# def payment_success(request):
#     return render(request, 'payment_success.html')

def payment_cancel(request):
    return render(request, 'payment_cancel.html')

def admin_dashboard(request):
    return render(request, 'dashboard.html')


def base_site(request):
    return render(request, 'base_site.html')


@staff_member_required
def manage_bikes(request):
    bikes = Bike.objects.all()
    form = BikeForm()
    return render(request, 'manage_bikes.html', {'bikes': bikes, 'form': form})

def get_bike_details(request, bike_id):
    bike = get_object_or_404(Bike, pk=bike_id)
    return JsonResponse({
        'id': bike.id,
        'name': bike.name,
        'description': bike.description,
        'price': str(bike.price),
        'available': bike.available,
        'stock': bike.stock,
        'image': bike.image.url if bike.image else None
    })

def update_bike(request, bike_id):
    bike = Bike.objects.get(pk=bike_id)

    if request.method == 'POST':
        bike.name = request.POST.get('name')
        bike.description = request.POST.get('description')
        bike.price = request.POST.get('price')
        # Handle the checkbox value for "Available" field
        bike.available = request.POST.get('available') == 'on'
        bike.stock = request.POST.get('stock')
        bike.save()
        return redirect('dashboard')

    return render(request, 'update_bike.html', {'bike': bike})


def delete_bike(request, bike_id):
    bike = Bike.objects.get(pk=bike_id)

    if request.method == 'POST':
        bike.delete()
        return redirect('admin_dashboard')  # Redirect to wherever you want

    return render(request, 'delete_bike.html', {'bike': bike})

def manage_bookings(request):
    bookings = Booking.objects.all()  # Retrieve all bookings
    return render(request, 'manage_bookings.html', {'bookings': bookings})


def confirm_bookings(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    booking.status = 'Confirmed'
    booking.save()
    messages.success(request, 'Booking confirmed successfully.')
    return redirect('admin_dashboard')

def cancel_bookings(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    booking.status = 'Cancelled'
    booking.save()
    messages.success(admin_dashboard, 'Booking cancelled successfully.')
    return redirect('dashboard')

def return_bookings(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    booking.status = 'admin_dashboard'
    booking.save()
    messages.success(request, 'Booking returned successfully.')
    return redirect('admin_dashboard')


def add_bike(request):
    if request.method == 'POST':
        form = BikeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')  # Redirect to manage bikes page after adding bike
    else:
        form = BikeForm()
    return render(request, 'add_bike.html', {'form': form})
