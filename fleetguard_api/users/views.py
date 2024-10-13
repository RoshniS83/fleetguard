# from django.shortcuts import render
# from rest_framework.exceptions import AuthenticationFailed
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from .serializers import UserSerializer
# from .models import User
# import jwt, datetime
# # Create your views here.
# class RegisterView(APIView):
#     def post(self, request):
#         serializer = UserSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)

# class LoginView(APIView):
#     def post(self, request):
#         email = request.data['email']
#         password = request.data['password']
#         user = User.objects.filter(email=email).first()
#         if user is None:
#             raise AuthenticationFailed('User not found!!')
#         if not user.check_password(password):
#             raise AuthenticationFailed('Incorrect password')

#         payload = {
#             'id' : user.id,
#             'exp':datetime.datetime.utcnow() + datetime.timedelta(hours=24),#token will live for 1 hour
#             'iat':datetime.datetime.utcnow()

#         }

#         token = jwt.encode(payload, 'secret', algorithm='HS256')

#         response =Response()
#         response.set_cookie(key='jwt', value=token, httponly=True)
#         response.data = {
#             'jwt':token
#         }
#         return response

# class UserView(APIView):
#     def get(self, request):
#         token = request.COOKIES.get('jwt')
#         if not token:
#             raise AuthenticationFailed("Unauthenticated user")

#         try:
#             payload = jwt.decode(token, 'secret', algorithms=['HS256'])
#         except jwt.ExpiredSignatureError:
#             raise AuthenticationFailed("Unauthenticated")

#         user = User.objects.filter(id=payload['id']).first()
#         if user is None:
#             raise AuthenticationFailed("User not found")

#         serializer = UserSerializer(user)
#         return Response(serializer.data)

# class LogoutView(APIView):
#     def post(self, request):
#         response = Response()
#         response.delete_cookie('jwt')
#         response.data = {
#             'message':'logout success'
#         }
#         return response

# from django.shortcuts import render
# from rest_framework.exceptions import AuthenticationFailed
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from .serializers import UserSerializer
# from .models import User
# import jwt, datetime
# # Create your views here.
# class RegisterView(APIView):
#     def post(self, request):
#         serializer = UserSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)
#
# class LoginView(APIView):
#     def post(self, request):
#         email = request.data['email']
#         password = request.data['password']
#         user = User.objects.filter(email=email).first()
#         if user is None:
#             raise AuthenticationFailed('User not found!!')
#         if not user.check_password(password):
#             raise AuthenticationFailed('Incorrect password')
#
#         payload = {
#             'id' : user.id,
#             'exp':datetime.datetime.utcnow() + datetime.timedelta(hours=24),#token will live for 1 hour
#             'iat':datetime.datetime.utcnow()
#
#         }
#
#         token = jwt.encode(payload, 'secret', algorithm='HS256')
#
#         response =Response()
#         response.set_cookie(key='jwt', value=token, httponly=True)
#         response.data = {
#             'jwt':token
#         }
#         return response




import re

import datetime
import jwt
import random
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
# from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import User, PasswordHistory
from .serializers import UserSerializer


def update_password(user, new_password):
    # Save old password to history
    old_password_hash = make_password(user.password)  # Hash the old password
    PasswordHistory.objects.create(user=user, email=user.email, old_password=old_password_hash)

    # Update the user's password
    user.set_password(new_password)
    user.password_last_changed = timezone.now()
    user.save()


def send_otp_email(user, recipient_email):
    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.otp_created_at = timezone.now()
    user.save()
    send_mail(
        'Your OTP Code',
        f'Your OTP code is {otp}',
        'chordzconnect@gmail.com',
        [user.email],
        fail_silently=False,
    )

def enforce_password_policies(user, new_password):
    if user:
    # Enforce password history (last 3 passwords)
        recent_passwords = PasswordHistory.objects.filter(user=user).order_by('-changed_at')[:3]
        for pwd_history in recent_passwords:
            if check_password(new_password, pwd_history.old_password):
                raise ValidationError({"message": "You cannot reuse your last 3 passwords"})

    # Critical password enforcement
    if len(new_password) < 8:
        raise ValidationError({"message":"Password must be at least 8 characters long"})

    if not re.search(r'[A-Z]', new_password):
        raise ValidationError({"message":"Password must contain at least one uppercase letter"})

    if not re.search(r'[a-z]', new_password):
        raise ValidationError({"message":"Password must contain at least one lowercase letter"})

    if not re.search(r'\d', new_password):
        raise ValidationError({"message":"Password must contain at least one digit"})

    if not re.search(r'[!@#$%^&*(),?":.<>|{}]', new_password):
        raise ValidationError({"message":"Password must contain at least one special character"})

    if user:
    # Save the new password to history
        PasswordHistory.objects.create(user=user, email=user.email, old_password=user.password)
        user.set_password(new_password)
    # Update user's password change date
        user.password_last_changed = timezone.now()
        user.save()


class RegisterView(APIView):
    def post(self, request):
        # try:
        email = request.data.get('email')
        password = request.data.get('password')
        emp_id= request.data.get('emp_id')
        if not email or not password :
            return Response({"message":" Email and Password are required "})
            # Check if the user with the given email already exists
        if User.objects.filter(email=email).exists():
            return Response({"message": "User with this email already exists."}, status=400)

        enforce_password_policies(None, password)  # Pass None for user as we are not creating the user yet

         # If password is valid, proceed with user creation
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Set the password
        user.set_password(password)
        user.save()

        return Response({"message": "Registered successfully"}, status=201)



class LoginView(APIView):
    def post(self, request):
        email = request.data['email']
        password = request.data['password']
        print(email, password)
        if not email or not password:
            raise ValidationError({'message': 'Email and password are required'})

        admin_user=User.objects.filter(role='Admin').first()
        if admin_user is None:
            admin_user=User.objects.create(name='Fleetguard Admin', email='admin@gmail.com', role='Admin')
            admin_user.set_password('Admin@123')
            admin_user.is_superuser= True
            admin_user.is_staff =True
            admin_user.save()

        user = User.objects.filter(email=email).first()

        if user is None:
            raise AuthenticationFailed('User not found!')
            # Check if the account is locked
        if user.account_locked:
            raise AuthenticationFailed({"message":"Account locked due to multiple failed login attempts. Please contact support "})

        if user.role == 'Admin':
            if not user.check_password(password):
                raise AuthenticationFailed({"message": "Incorrect Password"})

            response=Response()

            payload = {
                'id': user.id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            response.data = {
                'message':'Admin logged in successfully.You have the authority to create users',
                'id': user.id,
                'role': user.role,
                'jwt': token}
            response['Authorization'] = f'Bearer {token}'
            response.set_cookie(key='jwt', value=token, httponly=True)
            # response.set_cookie(key='jwt', value=response.data['jwt'], httponly=True)
            return response

        if user.role == 'User':
            user.is_staff=True
            if not user.check_password(password):
                user.login_attempts +=1
                if user.login_attempts >=3:
                    user.account_locked =True
                    user.save()
                    raise AuthenticationFailed('Account locked due to multiple incorrect password attempts')
                user.save()
                raise AuthenticationFailed('Incorrect Password')

            user.login_attempts = 0
            user.save()
            # Enforce password expiry (e.g., 90 days)
            if (timezone.now() - user.password_last_changed).days > 90:
                raise AuthenticationFailed({"message": "Password expired, please reset your password"})

            # Check if the user needs to change the password on first login
            if user.force_password_change:
                raise AuthenticationFailed({"message": "Please change your password on first logon"})
            payload = {
                'id': user.id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            response= Response()
            response.data= {
                'message': 'User logged in successfully.',
                'id': user.id,
                'role': user.role,
                'jwt': token
                }
            response['Authorization'] = f'Bearer {token}'
            response.set_cookie(key='jwt', value=response.data['jwt'], httponly=True)
            return response

        # Fallback response
        return Response({'message': 'Unexpected error occurred'}, status=500)


class UserView(APIView):
    def get(self, request):
        # Try to get the token from the Authorization header
        auth_header = request.headers.get('Authorization')
        token = None

        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]  # Extract the token from the 'Bearer ' prefix
        else:
            # If no Authorization header, try to get the token from cookies
            token = request.COOKIES.get('jwt')

        if not token:
            raise AuthenticationFailed({"message": "Unauthenticated user"})

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed({"message": "Token has expired"})
        except jwt.DecodeError:
            raise AuthenticationFailed({"message": "Invalid token"})
        except Exception as e:
            raise AuthenticationFailed({"message": str(e)})

        user = User.objects.filter(id=payload['id']).first()
        if user is None:
            raise AuthenticationFailed({"message": "User not found"})

        serializer = UserSerializer(user)
        return Response(serializer.data)



class LogoutView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie('jwt')
        response.data = {
            'message': 'Logout successful'
        }
        return response


class ChangePasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not email or not old_password or not new_password or not confirm_password:
            return Response({"message": "Email , Old password, new password and confirm password are required"}, status=400)

        user = User.objects.filter(email=email).first()

        if user is None:
            return Response({"message": "User not found!"}, status=404)

        if user.account_locked:
            return Response({"message":"Account locked due to multiple wrong password attempts"}, status=403)

        if new_password == old_password:
            return Response({"message":"You cannot use your last password"})

        if new_password != confirm_password:
            return Response({"message":"New password and confirm password do not match"}, status=400)
        # if not user.check_password(old_password):
                #return Response({"message":"Old password is incorrect"}, status=400)

        # Check if the old password is correct
        if not user.check_password(old_password):
            user.login_attempts += 1
            if user.login_attempts >= 3:
                user.account_locked = True
                user.save(update_fields=['login_attempts', 'account_locked'])
                return Response(
                        {
                            "message": "Account locked due to multiple incorrect password attempts. Please contact Admin support."},
                        status=403
                    )
            user.save(update_fields=['login_attempts'])
            remaining_attempts = 3 - user.login_attempts
            return Response(
                    {
                        "message": f"Old password is incorrect. {remaining_attempts} attempt(s) remaining before account lock."},
                    status=400
                )

            # Reset login attempts since the old password was correct
        user.login_attempts = 0
        user.save(update_fields=['login_attempts'])
        enforce_password_policies(user, new_password)
        # Set new password
        user.set_password(new_password)
        user.force_password_change = False  # Reset force password change flag
        user.password_last_changed = timezone.now()
        user.save(update_fields = ['password', 'force_password_change','password_last_changed'])
        # Save the new password to history after successfully changing it
        PasswordHistory.objects.create(user=user, email=user.email, old_password=user.password)
        return Response({"message": "Password changed successfully"})
class sendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        if user is None:
            raise AuthenticationFailed({"message": "User not found"})

        send_otp_email(user,email)
        return Response({"message": "OTP sent to your email"})

class OTPVerificationView(APIView):
    def post(self, request):
        # Retrieve email and OTP from request data
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"message": "Email and OTP are required"}, status=400)

        # Fetch user with the provided email
        user = User.objects.filter(email=email).first()

        if user is None:
            raise AuthenticationFailed({"message":"User not found"})

        # Check if the OTP matches and is within the validity period
        if user.otp != otp or (timezone.now() - user.otp_created_at).seconds > 300:
            raise AuthenticationFailed({"message": "Invalid or expired OTP"})

        # Clear OTP after successful verification
        user.otp = None
        user.otp_created_at = None  # Clear OTP creation time if it's stored
        user.save()

        return Response({"message": "OTP verified successfully"})

class AdminUserListView(APIView):
    # permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        # if request.user.role == 'user':
        #     raise PermissionDenied("You do not have permission to view this resource.")
        users = User.objects.filter(role='user')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class AdminChangePasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        # Fetch the user based on email
        user = User.objects.filter(email=email).first()

        if not user:
            return Response({"message": "User not found"}, status=404)

        if new_password != confirm_password:
            return Response({"message": "Passwords do not match"}, status=400)
            # Unlock the account if locked

        # Enforce password history (last 3 passwords)
        recent_passwords = PasswordHistory.objects.filter(user=user).order_by('-changed_at')[:3]
        for pwd_history in recent_passwords:
            if check_password(new_password, pwd_history.old_password):
                raise ValidationError({"message":"You cannot reuse your last 3 passwords"})

        # Critical password enforcement
        if len(new_password) < 8:
            raise ValidationError({"message":"Password must be at least 8 characters long"})
        if not re.search(r'[A-Z]', new_password):
            raise ValidationError({"message":"Password must contain at least one uppercase letter"})
        if not re.search(r'[a-z]', new_password):
            raise ValidationError({"message":"Password must contain at least one lowercase letter"})
        if not re.search(r'\d', new_password):
            raise ValidationError({"message":"Password must contain at least one digit"})
        if not re.search(r'[!@#$%^&*(),?":.<>|{}]', new_password):
            raise ValidationError({"message":"Password must contain at least one special character"})
        if user.account_locked:
            user.account_locked = False
            user.save()
        # Save the new password
        user.set_password(new_password)
        user.password_last_changed = timezone.now()
        user.force_password_change = False
        user.save()

        # Save the new password to history
        PasswordHistory.objects.create(user=user, email=user.email, old_password=user.password)



        return Response({"message": "Password changed and account unlocked successfully"})
