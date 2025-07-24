from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password_confirm', 
                 'first_name', 'last_name', 'access', 'refresh')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Password fields didn't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Add tokens to the user instance for serialization
        user.access = str(refresh.access_token)
        user.refresh = str(refresh)
        
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Structure response as specified in documentation
        return {
            'user': {
                'id': data['id'],
                'username': data['username'],
                'email': data['email'],
                'first_name': data['first_name'],
                'last_name': data['last_name']
            },
            'access': data['access'],
            'refresh': data['refresh']
        }


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid username or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            attrs['user'] = user
            attrs['access'] = str(refresh.access_token)
            attrs['refresh'] = str(refresh)
            
        else:
            raise serializers.ValidationError('Must include username and password.')
        
        return attrs

    def to_representation(self, instance):
        user = instance['user']
        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            'access': instance['access'],
            'refresh': instance['refresh']
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            raise serializers.ValidationError('Invalid or expired refresh token.') 