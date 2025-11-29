# Google OAuth Setup Guide

This guide will help you set up Google Sign-In for your application.

## Prerequisites

- A Google Cloud account
- Access to Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click on "Select a project" → "New Project"
3. Enter a project name (e.g., "Project Engine")
4. Click "Create"

## Step 2: Enable Google+ API

1. In your project, go to **APIs & Services** → **Library**
2. Search for "Google+ API" or "Identity Services API"
3. Click on it and enable it for your project

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** (unless you have a Google Workspace account)
3. Fill in the required information:
   - App name: Your application name
   - User support email: Your email
   - Developer contact information: Your email
4. Click "Save and Continue"
5. Add scopes (at minimum):
   - `email`
   - `profile`
   - `openid`
6. Click "Save and Continue"
7. Add test users if your app is in testing mode (optional)
8. Review and submit

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Choose **Web application** as the application type
4. Fill in the details:
   - **Name**: e.g., "Project Engine Web Client"
   - **Authorized JavaScript origins**: 
     - For development: `http://localhost:8080`
     - For production: `https://yourdomain.com`
   - **Authorized redirect URIs**: 
     - You can leave this empty for Google Identity Services (it's not needed for the one-tap flow)
5. Click **Create**
6. Copy the **Client ID** (you'll need this)

## Step 5: Configure Backend

1. Add the Google Client ID to your backend environment variables:
   
   Create or update your `.env` file in the `server/` directory:
   ```bash
   GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   ```

2. Install the required Python package (if not already installed):
   ```bash
   cd server
   pip install google-auth
   ```

3. Create and run the database migration for the `google_id` field:
   ```bash
   python manage.py makemigrations authentication
   python manage.py migrate
   ```

## Step 6: Configure Frontend

1. Add the Google Client ID to your frontend environment variables:
   
   Create or update your `.env` file in the `client/` directory:
   ```bash
   VITE_GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   ```

   Note: Make sure to use the same Client ID for both backend and frontend.

2. Restart your development server to load the new environment variable.

## Step 7: Test the Integration

1. Start your backend server:
   ```bash
   cd server
   docker-compose up
   # or
   python manage.py runserver
   ```

2. Start your frontend server:
   ```bash
   cd client
   npm run dev
   ```

3. Navigate to the login page
4. Click the "Continue with Google" button
5. Sign in with your Google account
6. You should be redirected to the dashboard upon successful authentication

## Troubleshooting

### "Google Client ID is not configured"
- Make sure you've added `VITE_GOOGLE_CLIENT_ID` to your frontend `.env` file
- Restart your development server after adding the environment variable

### "Invalid token" or "Invalid token audience"
- Verify that the Client ID in your `.env` files matches the one from Google Cloud Console
- Make sure you're using the Client ID (not the Client Secret) - Google Identity Services only needs the Client ID

### "Google OAuth is not configured on the server"
- Make sure you've added `GOOGLE_CLIENT_ID` to your backend `.env` file
- Restart your backend server after adding the environment variable

### Button doesn't appear
- Check your browser console for errors
- Verify that the Google Identity Services script is loading (check Network tab)
- Make sure `VITE_GOOGLE_CLIENT_ID` is set correctly

### Migration errors
- If you get errors about `google_id` field already existing, you may need to check your database migrations
- Run `python manage.py showmigrations authentication` to see migration status

## Security Notes

- Never commit your `.env` files to version control
- Use different Client IDs for development and production
- Regularly rotate your OAuth credentials
- Keep your Google Cloud project secure

## Additional Resources

- [Google Identity Services Documentation](https://developers.google.com/identity/gsi/web)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)

