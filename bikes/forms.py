from django import forms
from .models import Booking, Bike

class BookingForm(forms.ModelForm):
    # Define a hidden field for bike_id
    bike_id = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = Booking
        fields = ['bike_id', 'start_date', 'end_date']
class BikeForm(forms.ModelForm):

    class Meta:
        model = Bike
        fields = ['name', 'description', 'image', 'price', 'available', 'stock']
