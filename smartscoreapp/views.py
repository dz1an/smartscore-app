from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

def index(request):
    return render(request, 'index.html')

def login_view(request):
    if request.method == 'POST':
        # Assuming you have input fields with names 'username' and 'password' in your login form
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # User is valid, log them in
            login(request, user)
            # Redirect to a success page or homepage
            return redirect('index')  # Redirect to the index page after successful login
        else:
            # Authentication failed, return to login page with an error message
            return render(request, 'login.html', {'error_message': 'Invalid username or password'})

    # If request method is not POST or initial page load, render the login page
    return render(request, 'login.html')

def logout_view(request):
    # Your logout logic here
    # For example, you might clear the session or perform other cleanup tasks
    # Then, redirect the user to a specific page, such as the homepage
    return redirect('index') 
