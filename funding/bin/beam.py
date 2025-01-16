import requests
import json


class BEAMWalletAPI:
    def __init__(self, api_url):
        """
        Initialize the BEAM Wallet API client.

        :param api_url: The full URL to the BEAM Wallet API (e.g., 'http://127.0.0.1:10000')
        """
        self.api_url = api_url
        self.headers = {
            'Content-Type': 'application/json',
        }

    def _post(self, method, params=None):
        """
        Send a JSON-RPC request to the BEAM Wallet API.

        :param method: The API method to call (e.g., 'create_address').
        :param params: A dictionary of parameters for the API call.
        :return: The 'result' field from the API response.
        """
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': method,
            'params': params or {}
        }

        try:
            response = requests.post(self.api_url, headers=self.headers, data=json.dumps(payload))
            response.raise_for_status()  # Raise an exception for HTTP errors
            result = response.json()
            if 'error' in result:
                raise Exception(f"Error {result['error']['code']}: {result['error']['message']}")
            return result.get('result')
        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP Request failed: {e}")

    def create_address(self, label=None, expiration='never'):
        """
        Create a new BEAM payment address.

        :param label: A label for the address (optional).
        :param expiration: Address expiration ('never', '24h', '1w').
        :return: The newly created address.
        """
        params = {
            'comment': label,
            'expiration': expiration
        }
        return self._post('create_address', params)

    def get_balance(self):
        """
        Get the wallet's balance.

        :return: A dictionary containing balance details.
        """
        return self._post('wallet_status')

    def send_transaction(self, value, fee, receiver, comment=None):
        """
        Send a transaction to a specific address.

        :param value: The amount to send (in Groth, where 1 BEAM = 100,000,000 Groth).
        :param fee: The transaction fee (in Groth).
        :param receiver: The receiver's BEAM address.
        :param comment: An optional comment for the transaction.
        :return: The transaction ID.
        """
        params = {
            'value': value,
            'fee': fee,
            'address': receiver,
            'comment': comment
        }
        return self._post('tx_send', params)

    def get_transaction_status(self, tx_id):
        """
        Get the status of a specific transaction.

        :param tx_id: The transaction ID.
        :return: A dictionary containing transaction details.
        """
        params = {'tx_id': tx_id}
        return self._post('tx_status', params)

    def list_transactions(self):
        """
        List all wallet transactions.

        :return: A list of transactions.
        """
        return self._post('tx_list')

    def get_utxo(self):
        """
        Get UTXO (unspent transaction outputs) information.

        :return: A list of UTXOs.
        """
        return self._post('get_utxo')

    def delete_address(self, address):
        """
        Delete an address from the wallet.

        :param address: The address to delete.
        :return: A confirmation message.
        """
        params = {'address': address}
        return self._post('delete_address', params)

    def network_status(self):
        """
        Get the current network status.

        :return: A dictionary containing network information.
        """
        return self._post('network_status')