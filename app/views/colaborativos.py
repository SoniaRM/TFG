from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from ..forms import CustomUserCreationForm  

class SignupView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'colaborativo/signup.html'
    success_url = reverse_lazy('login')

