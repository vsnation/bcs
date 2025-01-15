import traceback
import uuid
from datetime import datetime

import requests
from flask import request, redirect, render_template, url_for, flash, make_response, send_from_directory, jsonify, session
from flask_login import login_user , logout_user , current_user
from dateutil.parser import parse as dateutil_parse
from flask_yoloapi import endpoint, parameter
import json
import markdown

from funding.bin.anti_xss import such_xss
import markdown2
import re

import settings
from funding.factory import app, db, cache
from funding.orm import Proposal, User, Comment




@app.route('/')
def index():
    proposals = Proposal.find_by_args(status=1) + Proposal.find_by_args(status=2) + \
                Proposal.find_by_args(status=3) + Proposal.find_by_args(status=4)
    return make_response(render_template('index.html', proposals=proposals, FUNDING_STATUSES=settings.FUNDING_STATUSES))


@app.route('/ideas')
@app.route('/funding-required')
@app.route('/work-in-progress')
@app.route('/completed-proposals')
def proposals_overview():
    # Map route paths to corresponding statuses
    route_status_mapping = {
        'ideas': 1,
        'funding-required': 2,
        'work-in-progress': 3,
        'completed-proposals': 4,
    }

    # Extract the current route name
    route_name = request.path.strip('/')

    # Get the corresponding status for the route
    status = route_status_mapping.get(route_name)
    if not status:
        return make_response("Page not found", 404)

    # Fetch proposals based on the determined status
    proposals = Proposal.find_by_args(status=status)

    # Render the appropriate template with variables
    return make_response(
        render_template(
            'proposal/overview.html',
            title=settings.FUNDING_STATUSES[status],
            proposals=proposals
        )
    )


# Open Edit proposal form
@app.route('/proposals/<slug>/edit')
def proposal_edit(slug):
    p = Proposal.query.filter_by(href=slug).first()
    if not p:
        return make_response(redirect(url_for('index')))

    funding_categories = settings.FUNDING_CATEGORIES  # Add categories from your settings
    return make_response(
        render_template(
            'proposal/edit.html',
            proposal=p,
            funding_categories=funding_categories,
            headline=p.headline,
            content=p.content,
            funds_target=p.funds_target,
            addr_receiving=p.addr_receiving
        )
    )


# Disclaimer before the form to add a proposal
@app.route('/disclaimer')
def proposal_add_disclaimer():
    return make_response(render_template('proposal/disclaimer.html'))

# Add proposal form
@app.route('/disclaimer/add')
def proposal_add():
    if current_user.is_anonymous:
        return make_response(redirect(url_for('login')))
    default_content = settings.PROPOSAL_CONTENT_DEFAULT
    return make_response(render_template('proposal/edit.html', default_content=default_content))

# Submit or Update Proposal data
@app.route('/api/proposals/upsert', methods=['POST'])
def proposal_api_upsert():
    # Ensure the request contains JSON
    data = request.get_json()
    if not data:
        return make_response(jsonify('Invalid request'), 400)

    # Extract fields from JSON payload
    title = data.get('title')
    content = data.get('markdown')
    pid = data.get('pid')
    funds_target = data.get('funds_target')
    addr_receiving = data.get('addr_receiving')
    discourse_topic_link = data.get('discourse_topic_link')
    category = data.get('category', settings.FUNDING_CATEGORIES[0])
    status = 1

    if current_user.is_anonymous:
        return make_response(jsonify('User not authenticated'), 401)

    # Validate inputs
    if not title or len(title) < 8:
        return make_response(jsonify('Title too short'), 400)

    if not content or len(content) < 20:
        return make_response(jsonify('Content too short'), 400)

    if category not in settings.FUNDING_CATEGORIES:
        return make_response(jsonify('Unknown category'), 400)

    # if status not in settings.FUNDING_STATUSES.keys():
    #     return make_response(jsonify('Unknown status'), 400)

    if status != 1 and not current_user.admin:
        return make_response(jsonify('Insufficient rights to change status'), 403)

    # Escape content and convert to HTML
    try:
        content_escaped = such_xss(content)
        html = markdown2.markdown(content_escaped, extras=["tables"], safe_mode="escape")
    except Exception as ex:
        return make_response(jsonify(f'Markdown error: {str(ex)}'), 500)

    # Helper function to create a slug for the `href`
    def generate_slug(headline):
        return re.sub(r'[^a-zA-Z0-9-]', '', headline.replace(' ', '-')).lower()

    if pid:
        # Edit existing proposal
        p = Proposal.find_by_id(pid=pid)
        if not p:
            return make_response(jsonify('Proposal not found'), 404)

        if p.user.id != current_user.id and not current_user.admin:
            return make_response(jsonify('No rights to edit this proposal'), 403)

        p.headline = title
        p.content = content
        p.html = html
        p.href = generate_slug(title)  # Update href
        p.discourse_topic_link = discourse_topic_link
        if addr_receiving:
            p.addr_receiving = addr_receiving
        if category:
            p.category = category

        # Handle status change with automated comment
        if p.status != status and current_user.admin:
            msg = f"Moved to status \"{settings.FUNDING_STATUSES[status].capitalize()}\"."
            try:
                Comment.add_comment(user_id=current_user.id, message=msg, pid=pid, automated=True)
            except:
                pass

        p.status = status
        p.last_edited = datetime.now()
    else:
        # Create new proposal
        try:
            funds_target = float(funds_target)
        except ValueError:
            return make_response(jsonify('Funds target must be a number'), 400)

        if funds_target < 1:
            return make_response(jsonify('Proposal asking less than 1 BEAM is not allowed'), 400)

        p = Proposal(
            headline=title,
            content=content,
            category=category,
            user=current_user
        )
        p.html = html
        p.href = generate_slug(title)  # Generate href for the new proposal
        p.last_edited = datetime.now()
        p.funds_target = funds_target
        p.addr_receiving = addr_receiving
        p.status = status
        p.addr_donation = "0x00000000"  # Placeholder for donation address
        p.payment_id = "0x00000000"  # Placeholder for payment ID
        p.discourse_topic_link = discourse_topic_link

        db.session.add(p)

    db.session.commit()
    db.session.flush()

    # Reset cached stats
    cache.delete('funding_stats')

    return make_response(jsonify({'url': url_for('proposals', slug=p.href)}))



@app.route('/about')
def about():
    return make_response(render_template('about.html'))

@app.route('/lib/markdown/html', methods=['POST'])
def markdown_to_html():
    try:
        # Parse the incoming JSON data
        data = request.json
        if not data or 'markdown' not in data:
            return jsonify({"error": "Markdown content is required"}), 400

        # Convert Markdown to HTML
        md_content = data['markdown']
        html_content = markdown.markdown(md_content, extensions=["fenced_code", "tables", "toc"])

        # Return the HTML content
        return jsonify({"html": html_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/proposals/<slug>')
def proposals(slug):
    # Check if the URL ends with `.md`
    if slug.endswith('.md'):
        # Strip the `.md` part to get the actual slug
        slug = slug[:-3]

        # Find the proposal by its href
        p = Proposal.query.filter_by(href=slug).first()
        if not p:
            return make_response("Proposal not found", 404)

        # Return the markdown content as plain text
        return make_response(p.content, 200, {'Content-Type': 'text/plain; charset=utf-8'})

    # Otherwise, render the proposal page
    else:
        p = Proposal.query.filter_by(href=slug).first()
        if not p:
            return make_response(redirect(url_for('index')))

        # Get associated comments and other data
        p.get_comments()
        return make_response(render_template('proposal/proposal.html', proposal=p, FUNDING_STATUSES=settings.FUNDING_STATUSES))


@app.route('/search', methods=['GET'])
def search():
    # Extract 'key' from query parameters
    key = request.args.get('key', default=None)

    if not key:
        return make_response(render_template('search.html', results=None, key='Empty!'))

    # Fetch search results based on the provided key
    results = Proposal.search(key=key)
    return make_response(render_template('search.html', results=results, key=key))


@app.route('/users/<username>', methods=['GET'])
def user_detail(username):
    """
    Show details for a specific user by username.
    """
    from funding.factory import db
    user = User.query.filter_by(username=username).first()
    if not user:
        return make_response(f"User '{username}' not found", 404)
    return render_template('user.html', user=user)


@app.route('/users', methods=['GET'])
def users():
    """
    List all users.
    """
    from funding.factory import db
    users = User.query.order_by(User.registered_on.desc()).all()
    return render_template('users.html', users=users)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if settings.USER_REG_DISABLED:
        return 'user reg disabled ;/'

    if request.method == 'GET':
        return make_response(render_template('register.html'))

    username = request.form['username']
    password = request.form['password']
    email = request.form['email']

    try:
        user = User.add(username, password, email)
        flash('Successfully registered. No confirmation email required. You can login!')
        cache.delete('funding_stats')  # reset cached stuffz
        return redirect(url_for('login'))
    except Exception as ex:
        flash('Could not register user. Probably a duplicate username or email that already exists.', 'error')
        return make_response(render_template('register.html'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return make_response(render_template('login.html'))

    # Extract form data manually
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Enter username/password pl0x')
        return make_response(render_template('login.html'))

    from funding.factory import bcrypt
    user = User.query.filter_by(username=username).first()
    if user is None or not bcrypt.check_password_hash(user.password, password):
        flash('Username or Password is invalid', 'error')
        return make_response(render_template('login.html'))

    login_user(user)
    response = redirect(request.args.get('next') or url_for('index'))
    response.headers['X-Set-Cookie'] = True
    return response


@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    response = redirect(request.args.get('next') or url_for('login'))
    response.headers['X-Set-Cookie'] = True
    return response


@app.route('/static/<path:path>')
def static_route(path):
    return send_from_directory('static', path)
