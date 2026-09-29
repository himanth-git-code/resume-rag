from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Project user model.

    Defined before the first migration so fields can be added later without
    a painful swap away from django.contrib.auth.models.User.
    """
