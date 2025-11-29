from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'username', 'name', 'date_joined')
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, label="Confirm Password", required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'name', 'password', 'password2')
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        password = data.get('password') or ''
        password2 = data.get('password2')
        
        # If password2 is provided, validate it matches
        if password2 and password != password2:
            raise serializers.ValidationError("Passwords do not match.")
        
        if len(password) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        email = data.get('email')
        username = data.get('username')
        
        # Auto-generate username from email if not provided
        if not username:
            # Extract username part from email (before @)
            username = email.split('@')[0]
            # Remove any special characters and make it unique if needed
            username = ''.join(c for c in username if c.isalnum() or c in ['_', '-'])
            # Ensure it's not empty
            if not username:
                username = 'user'
            # Make it unique by appending numbers if needed
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            data['username'] = username
        
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return data

    def create(self, validated_data):
        validated_data.pop('password2', None)
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            name=validated_data.get('name', ''),
            password=validated_data['password'],
        )
        return user

    def update(self, instance, validated_data):
        password = validated_data.get('password', None)
        if password:
            instance.set_password(password)
        instance.username = validated_data.get('username', instance.username)
        instance.name = validated_data.get('name', instance.name)
        try:
            instance.save()
        except Exception as e:
            raise serializers.ValidationError(f"Error updating user: {str(e)}")
        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError('Incorrect email or password.')
        data['user'] = user
        return data
