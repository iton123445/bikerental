from django.db import models
from django.contrib.auth.models import User

class Bike(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='bikes/', null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    available = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)  # Field for tracking stock

    def __str__(self):
        return self.name

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bike = models.ForeignKey(Bike, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status_choices = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned')
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='Pending')

    def __str__(self):
        return f"{self.user.username} - {self.bike.name}"

    @classmethod
    def get_user_bookings(cls, user):
        return cls.objects.filter(user=user)

    def save(self, *args, **kwargs):
        if self.pk is None:  # New booking
            if self.status == 'Confirmed' and self.bike.stock > 0:
                self.bike.stock -= 1
                self.bike.save()
        else:  # Existing booking
            original = Booking.objects.get(pk=self.pk)
            if original.status == 'Confirmed' and self.status == 'Returned':
                self.bike.stock += 1
                self.bike.save()
        super().save(*args, **kwargs)

    def confirm_return(self):
        if self.status == 'Confirmed':
            self.status = 'Returned'
            self.save()

class Transaction(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction for Booking: {self.booking.id}"
