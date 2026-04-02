"""
Contains the SheetsHandler class, which provides methods for interacting with Google Sheets.
This includes updating values, retrieving values, and incrementing cell values.
The class uses Google Sheets API for these operations and includes error handling
and logging for better traceability and debugging.
"""

import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.external_account_authorized_user import (
    Credentials as ExternalAccountCredentials,
)


class SheetsHandler:
    def __init__(
        self, sheet_id, creds: Credentials | ExternalAccountCredentials
    ) -> None:
        if not isinstance(creds, (Credentials, ExternalAccountCredentials)):
            raise TypeError(f"Expected Credentials object, got {type(creds)}")
        self.sheet_id = sheet_id
        self.creds = creds

    def update_values(
        self,
        spreadsheet_id,
        subsheet_id,
        range_name,
        _values,
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
                    valueInputOption="USER_ENTERED",
                    body=body,
                )
                .execute()
            )
            logging.info(
                "Updated %s cells in range '%s' on sheet '%s'.",
                result.get("updatedCells"),
                range_name,
                subsheet_id,
            )
            return result
        except HttpError as error:
            logging.error(
                "Failed to update values in range '%s' on sheet '%s': %s",
                range_name,
                subsheet_id,
                error,
            )
            return error

    def get_values(self, spreadsheet_id, subsheet_id, range_name):
        """Returns values from the spreadsheet from the specified range"""
        range_name = f"{subsheet_id}!{range_name}"
        try:
            service = build("sheets", "v4", credentials=self.creds)
            logging.info(
                "Attempting to retrieve values from range '%s' on sheet '%s'...",
                range_name,
                subsheet_id,
            )
            # pylint: disable=maybe-no-member
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            rows = result.get("values", [])
            logging.info(
                "Successfully retrieved %s rows from range '%s' on sheet '%s'.",
                len(rows),
                range_name,
                subsheet_id,
            )
            return result
        except HttpError as error:
            logging.error(
                "Failed to retrieve values from range '%s' on sheet '%s': %s",
                range_name,
                subsheet_id,
                error,
            )
            return error

    def increment_cell(self, cell, subsheet_id) -> int:
        """Increments the value of the given cell on the given subsheet by 1."""
        values = self.get_values(self.sheet_id, subsheet_id, cell)
        if isinstance(values, HttpError):
            logging.error(
                "Cannot increment cell '%s' on sheet '%s' due to error retrieving current value.",
                cell,
                subsheet_id,
            )
            raise values

        value = values.get("values", [])
        if not value or not value[0] or not value[0][0].isdigit():
            logging.warning(
                "Cell '%s' on sheet '%s' does not contain a valid integer value.",
                cell,
                subsheet_id,
            )
            raise ValueError(f"Invalid value in cell '{cell}' on sheet '{subsheet_id}'")

        new_value = int(value[0][0]) + 1
        self.update_values(self.sheet_id, subsheet_id, cell, [[new_value]])

        return new_value
