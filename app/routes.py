from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, jsonify
from werkzeug.urls import url_parse
from app import app, db
from app.forms import (
    LoginForm,
    RegistrationForm,
    EditProfileForm,
    EmptyForm,
    PostForm,
    ResetPasswordForm,
    ResetPasswordRequestForm,
    MessageForm,
    CommentForm,
    CommunityForm
)
from app.email import send_password_reset_email
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Post, Message, Notification, Comment, Community


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PostForm()
    page = request.args.get("page", 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, app.config["POSTS_PER_PAGE"], False
    )
    next_url = url_for("index", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("index", page=posts.prev_num) if posts.has_prev else None
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template(
        "index.html",
        title="Home",
        form=form,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("invalid username os password")
            return redirect(url_for("index"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)
    return render_template("login.html", title="Sign in", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("You have sucessfully registered!")
        return redirect(url_for("login"))
    return render_template("register.html", tittle="Register", form=form)


@app.route("/user/<username>")
@login_required
def user(username: str):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, app.config["POSTS_PER_PAGE"], False
    )
    next_url = (
        url_for("user", username=user.username, page=posts.next_num)
        if posts.has_next
        else None
    )
    prev_url = (
        url_for("user", username=user.username, page=posts.prev_num)
        if posts.has_prev
        else None
    )
    form = EmptyForm()
    return render_template(
        "user.html",
        user=user,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
        form=form,
    )


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your profile has been edited")
        return redirect(url_for("edit_profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me == current_user.about_me
    return render_template("edit_profile.html", tittle="Edit profile", form=form)


@app.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username: str):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash("User {} not found.".format(username))
            return redirect(url_for("index"))
        if user == current_user:
            flash("You cannot follow yourself!")
            return redirect(url_for("user", username=username))
        current_user.follow(user)
        db.session.commit()
        flash("You are following {}!".format(username))
        return redirect(url_for("user", username=username))
    else:
        return redirect(url_for("index"))


@app.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow(username: str):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash("User {} not found.".format(username))
            return redirect(url_for("index"))
        if user == current_user:
            flash("You cannot unfollow yourself!")
            return redirect(url_for("user", username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash("You are not following {}.".format(username))
        return redirect(url_for("user", username=username))
    else:
        return redirect(url_for("index"))


@app.route("/explore")
@login_required
def explore():
    community = Community.query.filter(Community.id == None)
    page = request.args.get("page", 1, type=int)
    posts = Post.query.filter(Post.communityid == None).order_by(Post.timestamp.desc()).paginate(
        page, app.config["POSTS_PER_PAGE"], False
    )
    next_url = url_for("explore", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("explore", page=posts.prev_num) if posts.has_prev else None
    return render_template(
        "index.html",
        title="Explore",
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
        community=community
    )


@app.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash("Additional confirmation sent to your E-mail")
        return redirect(url_for("login"))
    return render_template(
        "reset_password_request.html", tittle="Password Reset", form=form
    )


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset.")
        return redirect(url_for("login"))
    return render_template("reset_password.html", form=form)


@app.route("/send_message/<recipient>", methods=["GET", "POST"])
@login_required
def send_message(recipient: str):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user, body=form.message.data)
        db.session.add(msg)
        user.add_notification("unread_message_count", user.new_messages())
        db.session.commit()
        flash("Your message has been sent.")
        return redirect(url_for("user", username=recipient))
    return render_template(
        "send_message.html", title="Send Message", form=form, recipient=recipient
    )


@app.route("/deletemsg/<post_id>", methods=["GET", "POST"])
@login_required
def delete_message(post_id: int):
    post = Message.query.filter_by(id=post_id).first_or_404()
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("messages"))


@app.route("/deletepost/<post_id>", methods=["GET", "POST"])
@login_required
def delete_post(post_id: int):
    back = request.referrer
    post = Post.query.filter_by(id=post_id).first_or_404()
    db.session.delete(post)
    db.session.commit()
    return redirect(back)


@app.route("/deletecomm/<post_id>", methods=["GET", "POST"])
@login_required
def delete_comm(post_id: int):
    back = request.referrer
    post = Comment.query.filter_by(id=post_id).first_or_404()
    db.session.delete(post)
    db.session.commit()
    return redirect(back)


@app.route("/messages")
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification("unread_message_count", 0)
    db.session.commit()
    page = request.args.get("page", 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()
    ).paginate(page, app.config["POSTS_PER_PAGE"], False)
    next_url = (
        url_for("messages", page=messages.next_num) if messages.has_next else None
    )
    prev_url = (
        url_for("messages", page=messages.prev_num) if messages.has_prev else None
    )
    return render_template(
        "messages.html", messages=messages.items, next_url=next_url, prev_url=prev_url
    )


@app.route("/notifications")
@login_required
def notifications():
    since = request.args.get("since", 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since
    ).order_by(Notification.timestamp.asc())
    return jsonify(
        [
            {"name": n.name, "data": n.get_data(), "timestamp": n.timestamp}
            for n in notifications
        ]
    )


@app.route("/user/<username>/popup")
@login_required
def user_popup(username: str):
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template("user_popup.html", user=user, form=form)


@app.route("/<post_id>/<change>")
@login_required
def karma(post_id: int, change: str):
    back = request.referrer
    post = Post.query.filter_by(id=post_id).first_or_404()
    user = current_user
    postauthor = User.query.filter_by(id=post.user_id).first_or_404()
    if postauthor != user:
        if Post.karmachange(post, user, change, postauthor):
            if change == "+":
                flash("You have upvoted this post")
                return redirect(back)
            else:
                flash("You have downvoted this post")
                return redirect(back)
        else:
            flash("You cannot vote on the same post")
            return redirect(back)
    else:
        flash("You cannot vote on your own post")
        return redirect(back)


@app.route("/comment/<comment_id>/<change>")
@login_required
def karmacomm(comment_id: int, change: str):
    back = request.referrer
    comment = Comment.query.filter_by(id=comment_id).first_or_404()
    user = current_user
    postauthor = User.query.filter_by(id=comment.author_id).first_or_404()
    if postauthor != user:
        if Comment.karmachangecomm(comment, user, change, postauthor):
            if change == "+":
                flash("You have upvoted this comment")
                return redirect(back)
            else:
                flash("You have downvoted this comment")
                return redirect(back)
        else:
            flash("You cannot vote on the same comment")
            return redirect(back)
    else:
        flash("You cannot vote on your own comment")
        return redirect(back)


@app.route("/post/<post_id>", methods=["GET", "POST"])
@login_required
def post(post_id: int):
    post = Post.query.filter_by(id=post_id).first_or_404()
    form = CommentForm()
    page = request.args.get("page", 1, type=int)
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, post=post, author_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash("Your comment has been published.")
        return redirect(url_for("post", post_id=post.id, page=0))
    pagination = post.comments.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=app.config["POSTS_PER_PAGE"], error_out=False
    )
    comments = pagination.items
    next_url = (
        url_for("post", post_id=post.id, page=pagination.next_num)
        if pagination.has_next
        else None
    )
    prev_url = (
        url_for("post", post_id=post.id, page=pagination.prev_num)
        if pagination.has_prev
        else None
    )
    return render_template(
        "post.html",
        post=post,
        form=form,
        comments=comments,
        pagination=pagination,
        next_url=next_url,
        prev_url=prev_url,
    )
@app.route("/communities", methods=["GET", "POST"])
@login_required
def communities():

    form = CommunityForm()
    page = request.args.get("page", 1, type=int)
    posts = Community.query.order_by(Community.name.desc()).paginate(
        page, app.config["POSTS_PER_PAGE"], False
    )
    next_url = url_for("/community/<community_id>", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("/community/<community_id>", page=posts.prev_num) if posts.has_prev else None
    if form.validate_on_submit():
        community = Community(name=form.name.data, about=form.about.data)
        db.session.add(community)
        db.session.commit()
        return redirect(url_for("communities")) 
    return render_template(
        "community.html",
        title="Communities",
        form=form,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route("/community/<community_id>", methods=["GET", "POST"])
@login_required
def community(community_id):
    community = Community.query.filter(Community.id == community_id).first_or_404()
    form = PostForm()
    page = request.args.get("page", 1, type=int)
    posts = Post.query.filter(Post.communityid == community_id).order_by(Post.timestamp.desc()).paginate(
        page, app.config["POSTS_PER_PAGE"], False
    )
    next_url = url_for("/community/<community_id>", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("/community/<community_id>", page=posts.prev_num) if posts.has_prev else None
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user, communityid=community_id)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("community", community_id=community_id))
    return render_template(
        "community_id.html",
        title="<community_id>",
        form=form,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
        community=community
    )


@app.route("/community/<community_id>/join", methods=["GET","POST"])
@login_required
def followcomm(community_id: int):
    user=current_user
    community = Community.query.filter_by(id=community_id).first()
    community.followcomm(user)
    db.session.commit()
    flash("You have joined {}!".format(community.name))
    return redirect(url_for("community", community_id=community_id))



@app.route("/community/<community_id>/leave", methods=["GET","POST"])
@login_required
def unfollowcomm(community_id: int):
    user=current_user
    community = Community.query.filter_by(id=community_id).first()
    community.unfollowcomm(user)
    db.session.commit()
    flash("You have left {}.".format(community.name))
    return redirect(url_for("community", community_id=community_id))
