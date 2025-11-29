# Google OAuth Quick Setup - Step by Step

## Current Step: Configure OAuth Client

You're on the "Create OAuth client ID" page. Here's what to do:

### Step 1: Fill in the form

**Application type:** Already set to "Web application" ✅

**Name:** Already set to "projectEngine OAuth" ✅ (or you can rename it)

### Step 2: Add Authorized JavaScript origins

Click **"+ Add URI"** under "Authorized JavaScript origins" and add:

```
http://localhost:8080
```

**Why?** Your frontend runs on port 8080 (as configured in `client/vite.config.ts`).

**Optional:** If you sometimes run on a different port (like 5173), also add:
```
http://localhost:5173
```

### Step 3: Add Authorized redirect URIs (Optional)

For Google Identity Services, you can actually **leave this empty** (it's optional).

**OR** if you want to be safe, click **"+ Add URI"** and add:
```
http://localhost:8080
```

### Step 4: Click "Create"

After clicking "Create", you'll see a popup with:
- **Your Client ID** (looks like: `123456789-abc.apps.googleusercontent.com`)
- **Your Client Secret** (you don't need this!)

**⚠️ IMPORTANT:** Copy the **Client ID** (not the Client Secret) - you'll need it next!

---

## Next Steps After Creating the Client ID

### Step 5: Add Client ID to Backend

1. Open or create `server/.env` file
2. Add this line:
   ```bash
   GOOGLE_CLIENT_ID=paste-your-client-id-here.apps.googleusercontent.com
   ```

### Step 6: Add Client ID to Frontend

1. Open or create `client/.env` file
2. Add this line:
   ```bash
   VITE_GOOGLE_CLIENT_ID=paste-your-client-id-here.apps.googleusercontent.com
   ```
   
   ⚠️ **Use the SAME Client ID for both backend and frontend!**

### Step 7: Restart Your Servers

1. Restart your backend server
2. Restart your frontend server (`npm run dev`)

### Step 8: Test It!

1. Go to `http://localhost:8080/login`
2. You should see a "Sign in with Google" button
3. Click it and sign in with a Google account
4. You should be redirected to the dashboard! 🎉

---

## Troubleshooting

### "Redirect URI mismatch" error
- Make sure you added `http://localhost:8080` to Authorized JavaScript origins
- Make sure the URL matches exactly (including `http://` and port number)

### Button doesn't appear
- Check that `VITE_GOOGLE_CLIENT_ID` is set in `client/.env`
- Restart your frontend server after adding the variable

### "Invalid token" error
- Make sure both backend and frontend use the SAME Client ID
- Double-check you copied the Client ID correctly (no extra spaces)

---

## Summary

**On the Google Cloud Console page, add:**
- ✅ Authorized JavaScript origins: `http://localhost:8080`
- ⚪ Authorized redirect URIs: Leave empty (or add `http://localhost:8080`)

Then click **"Create"** and copy your Client ID!

