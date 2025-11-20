from django.contrib import admin
from .models import *
from users.models import *

admin.site.register(BalanceAccount)
admin.site.register(BalanceTransaction)
admin.site.register(Stock)
admin.site.register(News)
admin.site.register(Order)
admin.site.register(PortfolioItem)
admin.site.register(UserProfile)
admin.site.register(PhoneNumberCheck)
admin.site.register(KYCVerification)

