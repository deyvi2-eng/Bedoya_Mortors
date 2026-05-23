from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import BaseModel

class User(AbstractUser, BaseModel):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        SELLER = 'SELLER', 'Vendedor'

    role = models.CharField(
        max_length=10, 
        choices=Role.choices, 
        default=Role.SELLER,
        verbose_name="Rol del Usuario"
    )
    phone = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    def save(self, *args, **kwargs):
        # Si es superusuario o staff de Django, forzamos que sea ADMIN
        if self.is_superuser or self.is_staff:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)
        
    def is_admin(self):
        return self.role == self.Role.ADMIN
        
    def is_seller(self):
        return self.role == self.Role.SELLER

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"