# from django.contrib import admin

# # Register your models here.
# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from .models import User

# class UserAdmin(BaseUserAdmin):
#     model = User
#     list_display = ('email', 'username', 'is_staff', 'is_superuser', 'is_active')
#     list_filter = ('is_staff', 'is_superuser', 'is_active')
#     search_fields = ('email', 'username')
#     ordering = ('email',)
#     fieldsets = (
#         (None, {'fields': ('email', 'username', 'password')}),
#         ('Permissions', {'fields': ('is_staff', 'is_superuser', 'is_active')}),
#         ('Personal Info', {'fields': ('name', 'body_weight', 'gender')}),
#     )
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'username', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_active'),
#         }),
#     )

# admin.site.register(User, UserAdmin)
