import os
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def oauth_start(request):
    flow = Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, "client_secret.json"),
        scopes=SCOPES,
        redirect_uri=request.build_absolute_uri(reverse("oauth_callback")),
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    return redirect(auth_url)


def oauth_callback(request):
    state = request.session.get("oauth_state")
    flow = Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, "client_secret.json"),
        scopes=SCOPES,
        redirect_uri=request.build_absolute_uri(reverse("oauth_callback")),
        state=state,
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    creds = flow.credentials

    user_info = {
        "name": "YouTube User",
        "avatar": "",
    }

    try:
        youtube = build("youtube", "v3", credentials=creds)
        channel_response = youtube.channels().list(
            part="snippet",
            mine=True
        ).execute()
        
        if channel_response.get("items"):
            channel = channel_response["items"][0]["snippet"]
            user_info = {
                "name": channel.get("title", "YouTube User"),
                "avatar": channel.get("thumbnails", {}).get("default", {}).get("url", ""),
            }
    except Exception as e:
        print(f"Error fetching YouTube user info: {e}")

    request.session["yt_creds"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "user": user_info,  
    }
    return redirect("analyze")
