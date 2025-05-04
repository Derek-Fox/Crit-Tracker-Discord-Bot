import os
import logging

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class SheetsHandler:
    def __init__(self, sheet_id):
        self.sheet_id = sheet_id
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        self.creds = None
        if os.path.exists("token.json"):
            logging.info("Found token.json. Attempting to load credentials...")
            self.creds = Credentials.from_authorized_user_file("token.json", scopes)
        else:
            logging.warning("token.json not found. Beginning authentication...")

        if not self.creds or not self.creds.valid:
            try:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logging.info("Refreshing credentials...")
                    self.creds.refresh(Request())
                else:
                    logging.warning(
                        "No valid credentials found. Starting OAuth flow..."
                    )
                    raise RefreshError
            except RefreshError:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", scopes
                )
                flow.authorization_url(
                    access_type="offline", include_granted_scopes="true"
                )
                self.creds = flow.run_local_server(port=0)
                logging.info("OAuth flow completed successfully.")
            with open("token.json", "w", encoding="UTF-8") as token:
                token.write(self.creds.to_json())
                logging.info("Credentials saved to token.json")

    def update_values(
        self, spreadsheet_id, subsheet_id, range_name, value_input_option, _values
    ):
        """Updates values on the spreadsheet in the given range with given values"""
        range_name = f"{subsheet_id}!{range_name}"
        try:
            service = build("sheets", "v4", credentials=self.creds)
            body = {"values": _values}
            # pylint: disable=maybe-no-member
            result = (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body,
                )
                .execute()
            )
            logging.info(
                f"Updated {result.get('updatedCells')} cells in range '{range_name}' on sheet '{subsheet_id}'."
            )
            return result
        except HttpError as error:
            logging.error(
                f"Failed to update values in range '{range_name}' on sheet '{subsheet_id}': {error}"
            )
            return error

    def get_values(self, spreadsheet_id, subsheet_id, range_name):
        """Returns values from the spreadsheet from the specified range"""
        range_name = f"{subsheet_id}!{range_name}"
        try:
            service = build("sheets", "v4", credentials=self.creds)
            logging.info(
                f"Attempting to retrieve values from range '{range_name}' on sheet '{subsheet_id}'..."
            )
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            rows = result.get("values", [])
            logging.info(
                f"Successfully retrieved {len(rows)} rows from range '{range_name}' on sheet '{subsheet_id}'."
            )
            return result
        except HttpError as error:
            logging.error(
                f"Failed to retrieve values from range '{range_name}' on sheet '{subsheet_id}': {error}"
            )
            return error

    def get_and_update(self, cell, subsheet_id):
        """Increments the value of the given cell by 1."""
        value = self.get_values(self.sheet_id, subsheet_id, cell).get("values", [])

        self.pdate_values(
            self.sheet_id, subsheet_id, cell, "USER_ENTERED", [[int(value[0][0]) + 1]]
        )

        return int(value[0][0]) + 1
