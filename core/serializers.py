from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
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