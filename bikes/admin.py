from django.contrib import admin
from .models import Bike, Booking, Transaction

admin.site.register(Bike)
admin.site.register(Booking)
admin.site.register(Transaction)
