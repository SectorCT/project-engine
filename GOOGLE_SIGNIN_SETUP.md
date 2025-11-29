# Google Sign-In Setup Guide - Simple Steps

This guide will walk you through setting up Google Sign-In for your application step-by-step.

## How Google Sign-In Works

1. **User clicks "Sign in with Google"** → Google shows a login popup
2. **User signs in** → Google sends a special token (credential) back to your app
3. **Your app sends the token to your backend** → Backend verifies it's real with Google
4. **Backend creates/logs in the user** → Returns your app's authentication token
5. **User is logged in!** → Can access protected pages

## Step-by-Step Setup

### Step 1: Get Your Google Client ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. **Create a new project** (or select an existing one):
   - Click the project dropdown at the top
   - Click "New Project"
   - Enter a name like "Project Engine"
   - Click "Create"

3. **Enable Google Identity Services API**:
   - In the left menu, go to "APIs & Services" → "Library"
   - Search for "Google Identity Services API"
   - Click on it and click "Enable"

4. **Configure OAuth Consent Screen**:
   - Go to "APIs & Services" → "OAuth consent screen"
   - Choose "External" (unless you have Google Workspace)
   - Fill in:
     - App name: "Project Engine" (or your app name)
     - User support email: Your email
     - Developer contact: Your email
   - Click "Save and Continue"
   - On "Scopes" page, click "Save and Continue" (default scopes are fine)
   - On "Test users" page, click "Save and Continue" (skip for now)
   - Review and click "Back to Dashboard"

5. **Create OAuth Credentials**:
   - Go to "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS" → "OAuth client ID"
   - If prompted, choose "Web application"
   - Fill in:
     - Name: "Project Engine Web Client"
     - Authorized JavaScript origins:
       - For development: `http://localhost:5173` (or your frontend port)
       - Add `http://localhost:3000` if you use that port
     - Authorized redirect URIs: Leave empty (not needed for Google Identity Services)
   - Click "Create"
   - **Copy the Client ID** (it looks like: `123456789-abcdefg.apps.googleusercontent.com`)
   - ⚠️ **Important**: You only need the Client ID, NOT the Client Secret

### Step 2: Configure Your Backend

1. Open or create `server/.env` file (copy from `server/.envtemplate` if it doesn't exist)

2. Add your Google Client ID:
   ```bash
   GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   ```

3. Make sure `google-auth` is installed (it's already in `requirements.txt`):
   ```bash
   cd server
   pip install -r requirements.txt
   ```

4. Restart your backend server if it's running

### Step 3: Configure Your Frontend

1. Open or create `client/.env` file (copy from `client/.envtemplate` if it doesn't exist)

2. Add your Google Client ID:
   ```bash
   VITE_GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   ```
   
   ⚠️ **Important**: Use the SAME Client ID for both backend and frontend!

3. Restart your frontend development server:
   ```bash
   cd client
   npm run dev
   ```

### Step 4: Test It!

1. Make sure both backend and frontend servers are running
2. Go to your login page (`http://localhost:5173/login` or your port)
3. You should see a "Sign in with Google" button
4. Click it and sign in with a Google account
5. You should be redirected to the dashboard upon successful login! 🎉

## Troubleshooting

### Button doesn't appear or shows "Not Configured"
- ✅ Check that `VITE_GOOGLE_CLIENT_ID` is set in `client/.env`
- ✅ Restart your frontend server after adding the variable
- ✅ Check browser console for errors
- ✅ Make sure the Google script is loading (check Network tab in DevTools)

### "Invalid token" or "Invalid token audience" error
- ✅ Make sure `GOOGLE_CLIENT_ID` in backend matches frontend
- ✅ Double-check you copied the Client ID correctly (no extra spaces)
- ✅ Make sure the Client ID in Google Console matches what you're using

### "Google OAuth is not configured on the server" error
- ✅ Check that `GOOGLE_CLIENT_ID` is set in `server/.env`
- ✅ Restart your backend server after adding the variable

### "Redirect URI mismatch" error
- ✅ In Google Cloud Console, go to your OAuth client
- ✅ Make sure your frontend URL (e.g., `http://localhost:5173`) is in "Authorized JavaScript origins"
- ✅ Make sure you're using the exact same URL (including port)

### Button shows but nothing happens when clicked
- ✅ Check browser console for JavaScript errors
- ✅ Make sure the Google Identity Services script loaded (check Network tab)
- ✅ Verify your frontend URL matches what's in Google Console

## How to Find Your Client ID Again

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to "APIs & Services" → "Credentials"
4. Click on your OAuth 2.0 Client ID
5. Copy the "Client ID" (not the Client Secret)

## For Production

When deploying to production:

1. **Create a new OAuth Client ID** for production (or use the same one)
2. **Add your production domain** to "Authorized JavaScript origins":
   - Example: `https://yourdomain.com`
   - Example: `https://www.yourdomain.com`
3. **Update your production environment variables** with the Client ID
4. **Make sure your OAuth consent screen is published** (if you want anyone to use it)

## Security Notes

- ✅ Never commit `.env` files to git (they're already in `.gitignore`)
- ✅ Use different Client IDs for development and production if possible
- ✅ The Client ID is safe to expose in frontend code (it's meant to be public)
- ✅ Never share your Client Secret (but you don't need it for Google Identity Services)

## What Files Are Involved?

The Google Sign-In is already implemented in these files:

**Frontend:**
- `client/src/pages/Login.tsx` - The login page with the Google button
- `client/src/contexts/AuthContext.tsx` - Handles Google login
- `client/src/lib/api.ts` - Sends the Google token to backend
- `client/index.html` - Loads Google Identity Services script

**Backend:**
- `server/authentication/views.py` - Verifies Google token and creates/logs in user
- `server/authentication/urls.py` - Route for `/api/auth/google/`
- `server/authentication/models.py` - User model with `google_id` field
- `server/server/settings.py` - Reads `GOOGLE_CLIENT_ID` from environment

You don't need to modify any of these files - just configure the environment variables!

## Need Help?

- Check the detailed guide: `GOOGLE_OAUTH_SETUP.md`
- Google Identity Services docs: https://developers.google.com/identity/gsi/web
- Google Cloud Console: https://console.cloud.google.com/

