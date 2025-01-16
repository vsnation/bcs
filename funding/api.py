import re

import requests
from flask import jsonify, send_from_directory, Response, request
from flask_yoloapi import endpoint, parameter

from funding.bin.utils import get_ip
from funding.bin.qr import QrCodeGenerator
from funding.factory import app, cache
from funding.orm import Proposal


@app.route('/api/1/proposals', methods=['GET'])
def api_proposals_get():
    # Extract query parameters manually
    status = request.args.get('status', default=1, type=int)
    cat = request.args.get('cat', default=None, type=str)
    limit = request.args.get('limit', default=20, type=int)
    offset = request.args.get('offset', default=0, type=int)

    try:
        # Fetch proposals with the extracted parameters
        proposals = Proposal.find_by_args(status=status, cat=cat, limit=limit, offset=offset)
    except Exception as ex:
        print(ex)
        return jsonify({'error': 'Failed to fetch proposals'}), 500

    # Return proposals as JSON
    return jsonify([p.json for p in proposals])


@app.route('/api/1/convert/beam-usd', methods=['GET'])
def api_coin_usd():
    # Extract 'amount' from query parameters
    amount = request.args.get('amount', type=int)
    if amount is None:
        return jsonify({'error': 'Missing required parameter: amount'}), 400

    try:
        from funding.bin.utils import Summary, coin_to_usd
        prices = Summary.fetch_prices()
        usd_value = coin_to_usd(amt=amount, coin_usd=prices['coin-usd'])
    except Exception as ex:
        print(ex)
        return jsonify({'error': 'Failed to fetch conversion rate'}), 500

    return jsonify({'usd': usd_value})


@app.route('/api/1/qr', methods=['GET'])
def api_qr_generate():
    # Extract 'address' from query parameters
    address = request.args.get('address', type=str)
    if not address:
        return jsonify({'error': 'Missing required parameter: address'}), 400

    from funding.factory import cache
    qr = QrCodeGenerator()

    try:
        # Check if QR code already exists
        if not qr.exists(address):
            ip = get_ip()
            cache_key = f'qr_ip_{ip}'
            hit = cache.get(cache_key)

            if hit and ip not in ['127.0.0.1', 'localhost']:
                return Response('Wait a bit before generating a new QR', 403)

            throttling_seconds = 3
            cache.set(cache_key, {'wow': 'kek'}, throttling_seconds)

            # Create the QR code
            created = qr.create(address)
            if not created:
                raise Exception('Could not create QR code')
    except Exception as ex:
        print(ex)
        return jsonify({'error': 'Failed to generate QR code'}), 500

    # Serve the QR code image
    return send_from_directory('static/qr', f'{address}.png')
