import json
import logging
import datetime
import requests
import uuid

# import functions
from flask import render_template, session, request, redirect, url_for
from flask import Blueprint
from utils.udp import SESSION_INSTANCE_SETTINGS_KEY, get_app_vertical, get_udp_ns_fieldname, apply_remote_config
from utils.okta import TokenUtil, OktaAdmin
from utils.email import Email
from urllib.parse import urlparse

from GlobalBehaviorandComponents.validation import is_authenticated, get_userinfo
from GlobalBehaviorandComponents.mfaenrollment import get_enrolled_factors

logger = logging.getLogger(__name__)

# set blueprint
ecommerce_views_bp = Blueprint('ecommerce_views_bp', __name__, template_folder='templates', static_folder='static', static_url_path='static')


# Required for Login Landing Page
@ecommerce_views_bp.route("/profile")
@apply_remote_config
@is_authenticated
def ecommerce_profile():
    logger.debug("ecommerce_profile()")
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user_info = get_userinfo()
    user_info2 = okta_admin.get_user(user_info["sub"])
    factors = get_enrolled_factors(user_info["sub"])

    if get_udp_ns_fieldname("consent") in user_info2["profile"]:
        consent = user_info2["profile"][get_udp_ns_fieldname("consent")]
        if consent.strip() == "":
            consent = ''
            session['appointment'] = "No Appointments Currently Set."
    else:
        consent = ''

    crediturl = ''
    app_info = okta_admin.get_applications_by_user_id(user_info["sub"])
    for item in app_info:
        if "credit Demo (Generated by UDP)" in item["label"]:
            domain = urlparse(item["settings"]["oauthClient"]["initiate_login_uri"]).netloc
            crediturl = "https://" + domain

    return render_template(
        "ecommerce/profile.html",
        id_token=TokenUtil.get_id_token(request.cookies),
        access_token=TokenUtil.get_access_token(request.cookies),
        user_info=user_info,
        user_info2=user_info2,
        consent=consent,
        factors=factors,
        config=session[SESSION_INSTANCE_SETTINGS_KEY],
        crediturl=crediturl)


# Account Page
@ecommerce_views_bp.route("/account")
@apply_remote_config
@is_authenticated
def ecommerce_account():
    logger.debug("ecommerce_account()")
    return render_template("ecommerce/account.html", user_info=get_userinfo(), config=session[SESSION_INSTANCE_SETTINGS_KEY], _scheme="https")


@ecommerce_views_bp.route("/shop")
@apply_remote_config
def ecommerce_shop():
    logger.debug("ecommerce_shop()")
    products = requests.get(url=session[SESSION_INSTANCE_SETTINGS_KEY]["settings"]["app_ecomm_products"])

    return render_template(
        "ecommerce/shop.html",
        templatename=get_app_vertical(),
        products=products.json(),
        config=session[SESSION_INSTANCE_SETTINGS_KEY],
        user_info=get_userinfo(),
        _scheme="https")


@ecommerce_views_bp.route("/product/<product_id>")
@apply_remote_config
def ecommerce_product(product_id):
    logger.debug("ecommerce_product()")
    products = requests.get(url=session[SESSION_INSTANCE_SETTINGS_KEY]["settings"]["app_ecomm_products"])

    return render_template(
        "ecommerce/product.html",
        templatename=get_app_vertical(),
        products=products.json(),
        user_info=get_userinfo(),
        productid=product_id,
        config=session[SESSION_INSTANCE_SETTINGS_KEY],
        _scheme="https")


# checkout Page
@ecommerce_views_bp.route("/checkout")
@apply_remote_config
@is_authenticated
def ecommerce_checkout():
    logger.debug("ecommerce_checkout()")
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user = okta_admin.get_user(user_info["sub"])

    return render_template("ecommerce/checkout.html", user=user, user_info=get_userinfo(), config=session[SESSION_INSTANCE_SETTINGS_KEY], _scheme="https")


# Required for Registration Page
@ecommerce_views_bp.route("/registration")
@apply_remote_config
def ecommerce_registration():
    logger.debug("ecommerce_registration()")
    return render_template(
        "ecommerce/pp_registration.html",
        templatename=get_app_vertical(),
        config=session[SESSION_INSTANCE_SETTINGS_KEY],
        _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"])


@ecommerce_views_bp.route("/registration-completion", methods=["POST"])
@apply_remote_config
def ecommerce_registration_completion():
    logger.debug("ecommerce_registration_completion()")
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user_create_response = None
    user_data = {
        "profile": {}
    }
    logger.debug(user_data)
    logger.debug(request.form.get('guestUserId'))
    guestUserID = request.form.get('guestUserId')
    if guestUserID:
        user_data = okta_admin.get_user(request.form.get('guestUserId'))

    user_data["profile"]["email"] = request.form.get('email')
    user_data["profile"]["login"] = request.form.get('email')
    user_data["profile"]["firstName"] = "Guest"
    user_data["profile"]["lastName"] = "User"

    if "id" in user_data:
        user_create_response = okta_admin.update_user(user_id=user_data["id"], user=user_data)
    else:
        user_create_response = okta_admin.create_user(user=user_data, activate_user='false')

    logger.debug(user_create_response)

    if "id" not in user_create_response:
        error_message = "Failed to get a valid response from Okta Create User: user_data:{0} user_create_response:{1}".format(user_data, user_create_response)
        logger.error(error_message)

        return render_template(
            "/error.html",
            templatename=get_app_vertical(),
            config=session[SESSION_INSTANCE_SETTINGS_KEY],
            error_message=error_message)

    activation_link = ""
    if request.form.get('noemail').lower() == 'true':
        logger.debug("no email will be sent")
        activation_link = url_for(
            "gbac_registration_bp.gbac_registration_state_get",
            stateToken=user_create_response["id"],
            _external=True,
            _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"])
    else:
        logger.debug("email sent")
        ecommerce_email_registration(
            recipient={"address": request.form.get('email')},
            token=user_create_response["id"])

    return render_template(
        "ecommerce/registration-completion.html",
        email=request.form.get('email'),
        activationlink=activation_link,
        noemail=request.form.get('noemail').lower(),
        templatename=get_app_vertical(),
        config=session[SESSION_INSTANCE_SETTINGS_KEY],
        _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"])


# Create Guest Account
@ecommerce_views_bp.route("/create-guest")
@apply_remote_config
def ecommerce_create_guest_account():
    logger.debug("ecommerce_create_guest_account()")
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    guest_user_id = str(uuid.uuid4()).replace('-', '')

    user_data = {
        "profile": {
            "email": "{id}@guestuseraccount.com".format(id=guest_user_id),
            "login": "{id}@guestuseraccount.com".format(id=guest_user_id),
            "firstName": "Guest",
            "lirstName": "User",
        }
    }

    response = okta_admin.create_user(user=user_data)
    return response


# Apply Credit Page
@ecommerce_views_bp.route("/apply")
@apply_remote_config
@is_authenticated
def ecommerce_apply():
    logger.debug("ecommerce_apply()")
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user = okta_admin.get_user(user_info["sub"])

    return render_template("ecommerce/apply.html", user=user, user_info=get_userinfo(), config=session[SESSION_INSTANCE_SETTINGS_KEY], _scheme="https")


# Order Page
@ecommerce_views_bp.route("/order", methods=["GET"])
@apply_remote_config
@is_authenticated
def ecommerce_order():
    logger.debug("ecommerce_order()")
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user = okta_admin.get_user(user_info["sub"])

    return render_template("ecommerce/order.html", user=user, user_info=get_userinfo(), config=session[SESSION_INSTANCE_SETTINGS_KEY], _scheme="https")


# Order Page
@ecommerce_views_bp.route("/order_post", methods=["POST"])
@apply_remote_config
@is_authenticated
def ecommerce_order_post():
    logger.debug("ecommerce_order_post()")
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])

    logger.debug(request)
    firstname = request.form.get("firstName")
    lastname = request.form.get("lastName")
    email = request.form.get("email")
    streetAddress = request.form.get("address")
    city = request.form.get("city")
    state = request.form.get("state")
    zipCode = request.form.get("zip")
    countryCode = request.form.get("country")

    user_data = {
        "profile": {
            "firstName": firstname,
            "lastName": lastname,
            "email": email,
            "streetAddress": streetAddress,
            "city": city,
            "state": state,
            "zipCode": zipCode,
            "countryCode": countryCode
        }
    }
    logger.debug(user_data)
    response = okta_admin.update_user(user_id=user_info["sub"], user=user_data)
    logger.debug(response)

    # /ecommerce/order?message=Order Complete
    # return render_template("ecommerce/order.html", user=user, user_info=get_userinfo(), config=session[SESSION_INSTANCE_SETTINGS_KEY], _scheme="https")
    return redirect(
        url_for(
            "ecommerce_views_bp.ecommerce_order",
            _external="True",
            _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"],
            message="Order Complete"))


# updateuser Page
@ecommerce_views_bp.route("/updateuser")
@apply_remote_config
@is_authenticated
def ecommerce_updateuser():
    logger.debug("ecommerce_updateuser()")
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    logger.debug(request)

    firstname = request.args["firstName"]
    lastname = request.args["lastName"]
    email = request.args["email"]
    primaryPhone = request.args["phone"]
    mobilePhone = request.args["phone"]
    streetAddress = request.args["streetAddress"]
    city = request.args["city"]
    state = request.args["state"]
    zipCode = request.args["zipCode"]
    countryCode = request.args["countryCode"]

    user_data = {
        "profile": {
            "firstName": firstname,
            "lastName": lastname,
            "email": email,
            "primaryPhone": primaryPhone,
            "mobilePhone": mobilePhone,
            "streetAddress": streetAddress,
            "city": city,
            "state": state,
            "zipCode": zipCode,
            "countryCode": countryCode
        }
    }
    logger.debug(user_data)
    response = okta_admin.update_user(user_id=user_info["sub"], user=user_data)
    logger.debug(response)
    return response


# See if credit app exists
@ecommerce_views_bp.route("/credit")
@apply_remote_config
def ecommerce_credit():
    logger.debug("ecommerce_credit()")
    return render_template(
        "ecommerce/credit.html",
        templatename=get_app_vertical(),
        config=session[SESSION_INSTANCE_SETTINGS_KEY],
        user_info=get_userinfo(),
        _scheme="https")


@ecommerce_views_bp.route("/clearconsent/<userid>")
@apply_remote_config
@is_authenticated
def ecommerce_clear_consent(userid):
    logger.debug("ecommerce_clear_consent")
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])

    user_data = {"profile": {
        get_udp_ns_fieldname("consent"): "",
    }}

    user_update_response = okta_admin.update_user(userid, user_data)

    if "error" in user_update_response:
        message = "Error During Update: " + user_update_response
    else:
        message = ""

    return redirect(
        url_for(
            "ecommerce_views_bp.ecommerce_profile",
            _external="True",
            _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"],
            user_id=userid,
            message=message))


@ecommerce_views_bp.route("/acceptterms")
@apply_remote_config
@is_authenticated
def ecommerce_accept_terms():
    logger.debug("ecommerce_accept_terms()")
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user = okta_admin.get_user(user_info["sub"])
    user_id = user["id"]

    now = datetime.datetime.now()
    # dd/mm/YY H:M:S
    consent = now.strftime("%d/%m/%Y %H:%M:%S")

    user_data = {"profile": {get_udp_ns_fieldname("consent"): consent}}
    user_update_response = okta_admin.update_user(user_id, user_data)
    if user_update_response:
        message = "Thank you for completing the Consent Form."
    else:
        message = "Error During consent"

    return redirect(
        url_for(
            "ecommerce_views_bp.ecommerce_profile",
            _external="True",
            _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"],
            user_id=user_id,
            message=message))


@ecommerce_views_bp.route("/workflow-requests", methods=["GET"])
@apply_remote_config
@is_authenticated
def ecommerce_requests_get():
    logger.debug("workflow_requests_get()")

    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user = okta_admin.get_user(user_info["sub"])
    user_id = user["id"]

    if get_udp_ns_fieldname("access_requests") in user["profile"]:
        pendingRequest = user["profile"][get_udp_ns_fieldname("access_requests")]
    else:
        pendingRequest = []

    workflow_list = []

    # On a GET display the registration page with the defaults
    list_group_user = []
    list_group_full = []

    # Find the groups the user belongs to
    get_user_groups_response = okta_admin.get_user_groups(user_id=user_id)
    CONFIG_GROUP_EMPLOYEE_STARTSWITH = get_udp_ns_fieldname("employee")
    CONFIG_GROUP_BUYER_STARTSWITH = get_udp_ns_fieldname("buyer")
    print(CONFIG_GROUP_BUYER_STARTSWITH)
    companylist = []
    buyerlist = []
    for item in get_user_groups_response:
        if item["profile"]["name"].startswith(CONFIG_GROUP_EMPLOYEE_STARTSWITH):
            group_id = "{id}".format(id=item["id"])
            companylist.append(item["profile"]["name"].replace(CONFIG_GROUP_EMPLOYEE_STARTSWITH, ""))

    for item in get_user_groups_response:
        if item["profile"]["name"].startswith(CONFIG_GROUP_BUYER_STARTSWITH):
            group_id = "{id}".format(id=item["id"])
            buyerlist.append(item["profile"]["name"].replace(CONFIG_GROUP_BUYER_STARTSWITH, ""))

    get_groups = okta_admin.get_groups_by_name(get_udp_ns_fieldname(""))
    for item in get_groups:
        if item["profile"]["name"].replace(CONFIG_GROUP_BUYER_STARTSWITH, "") in companylist:
            if item["profile"]["name"].replace(CONFIG_GROUP_BUYER_STARTSWITH, "") not in buyerlist:
                group_id = "{id}".format(id=item["id"])
                list_group_full.append({
                    "id": item["id"],
                    "name": item["profile"]["name"],
                    "description": item["profile"]["description"],
                    "status": "Pending" if group_id in pendingRequest else "Not Requested"
                })

    # Populate the workflow list with groups that the user is absent in
    set_list1 = set(tuple(sorted(d.items())) for d in list_group_full)
    set_list2 = set(tuple(sorted(d.items())) for d in list_group_user)

    set_difference = set_list1 - set_list2
    for tuple_element in set_difference:
        workflow_list = list_group_full

    return render_template(
        "{0}/workflow-requests.html".format(get_app_vertical()),
        templatename=get_app_vertical(),
        user_info=user_info,
        workflow_list=workflow_list,
        config=session[SESSION_INSTANCE_SETTINGS_KEY],
        _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"])


@ecommerce_views_bp.route("/workflow-requests", methods=["POST"])
@apply_remote_config
@is_authenticated
def ecommerce_requests_post():
    logger.debug("workflow_requests_post()")
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user = okta_admin.get_user(user_info["sub"])
    user_id = user["id"]
    if get_udp_ns_fieldname("access_requests") in user["profile"]:
        pendingRequest = user["profile"][get_udp_ns_fieldname("access_requests")]
    else:
        pendingRequest = []

    if request.form.get("request_access"):
        group_id = request.form.get("request_access")
        if group_id not in pendingRequest:
            pendingRequest.append(group_id)

        # Remove user attribute organization ( as the request has been rejected)
        # organization": "[ '{id}' ]".format(id=request.form.get('location'))
        user_data = {
            "profile": {
                get_udp_ns_fieldname("access_requests"): pendingRequest
            }
        }
        test = okta_admin.update_user(user_id=user_id, user=user_data)
        print(test)
        ecommerce_emailWorkFlowRequest(group_id)

    return redirect(url_for("ecommerce_views_bp.ecommerce_requests_get", _external=True, _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"]))


@ecommerce_views_bp.route("/workflow-approvals", methods=["GET"])
@apply_remote_config
@is_authenticated
def ecommerce_approvals_get():
    logger.debug("workflow_approvals()")

    workflow_list = []
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user = okta_admin.get_user(user_info["sub"])
    user_groups = okta_admin.get_user_groups(user["id"])

    user_get_response = okta_admin.get_user_list_by_search(
        'profile.{0} pr  '.format(get_udp_ns_fieldname("access_requests")))
    for list in user_get_response:
        for grp in list["profile"][get_udp_ns_fieldname("access_requests")]:
            group_get_response = okta_admin.get_group(id=grp)
            logging.debug(group_get_response)
            var = {
                "requestor": list["profile"]["login"],
                "request": group_get_response["profile"]["description"],
                "usr_grp": {"user_id": list["id"], "group_id": grp}
            }
            for clist in user_groups:
                if grp == clist['id']:
                    workflow_list.append(var)

    return render_template(
        "{0}/workflow-approvals.html".format(get_app_vertical()),
        templatename=get_app_vertical(),
        workflow_list=workflow_list,
        user_info=user_info,
        config=session[SESSION_INSTANCE_SETTINGS_KEY],
        _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"])


@ecommerce_views_bp.route("/workflow-approvals", methods=["POST"])
@apply_remote_config
@is_authenticated
def ecommerce_approvals_post():
    logger.debug("workflow_approvals()")
    user_info = get_userinfo()
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user = okta_admin.get_user(user_info["sub"])
    user_id = user["id"]

    if request.form.get("action") == "reject":
        req = request.form.get("action_value")
        req = req.replace("\'", "\"")
        req = json.loads(req)
        user_id = req["user_id"]
        group_id = req["group_id"]
        user_wf = okta_admin.get_user(user_id)

        grps = user_wf["profile"][get_udp_ns_fieldname("access_requests")]
        grps.remove(group_id)

        # Remove user attribute organization ( as the request has been rejected)
        user_data = {
            "profile": {
                get_udp_ns_fieldname("access_requests"): grps
            }
        }
        okta_admin.update_user(user_id=user_id, user=user_data)

    if request.form.get("action") == "approve":
        req = request.form.get("action_value")
        req = req.replace("\'", "\"")
        req = json.loads(req)
        user_id = req["user_id"]
        group_id = req["group_id"]

        # Assign user to group
        okta_admin.assign_user_to_group(group_id, user_id)

        user_wf = okta_admin.get_user(user_id)

        grps = user_wf["profile"][get_udp_ns_fieldname("access_requests")]
        grps.remove(group_id)

        # Remove user attribute organization ( as the request has been rejected)
        user_data = {
            "profile": {
                get_udp_ns_fieldname("access_requests"): grps
            }
        }
        okta_admin.update_user(user_id=user_id, user=user_data)

    return redirect(url_for("ecommerce_views_bp.ecommerce_approvals_get", _external=True, _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"]))


# EMail workflow Request to the Admin
def ecommerce_emailWorkFlowRequest(group_id):
    logger.debug("emailWorkFlowRequest()")
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])

    activation_link = url_for("ecommerce_views_bp.ecommerce_approvals_get", _external=True, _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"])
    # Send Activation Email to the Admin
    subject_admin = "A workflow request was received"
    message_admin = """\
        <p><h1>A new request for access was received.</h1><br>
           The request is awaiting your approval.<br><br>
           Click this link to log into your account and review the request<br><br>
           <a href='{activation_link}'>{activation_link}</a>
        </p>
    """.format(activation_link=activation_link)

    # Find All members that will be notified
    recipients = []
    user_list = okta_admin.get_user_list_by_group_id(group_id)
    for user in user_list:
        recipients.append({"address": user["profile"]["email"]})

    if recipients:
        email_send = Email.send_mail(subject=subject_admin, message=message_admin, recipients=recipients)
        return email_send
    else:
        return ''


@ecommerce_views_bp.route("/updateuserinfo", methods=["POST"])
@apply_remote_config
@is_authenticated
def ecommerce_user_update():
    logger.debug("ecommerce_user_update")
    okta_admin = OktaAdmin(session[SESSION_INSTANCE_SETTINGS_KEY])
    user_id = request.form.get('user_id')
    logging.debug(request.form.to_dict())

    first_name = safe_get_dict(request.form, 'firstname')
    last_name = safe_get_dict(request.form, 'lastname')
    email = safe_get_dict(request.form, 'email')
    mobile_phone = safe_get_dict(request.form, 'mobilePhone')
    consent = safe_get_dict(request.form, 'nconsent')

    user_data = {"profile": {
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "mobilePhone": mobile_phone,
        get_udp_ns_fieldname("consent"): consent,
    }}

    logging.debug(user_data)
    user_update_response = okta_admin.update_user(user_id, user_data)
    logging.debug(user_update_response)

    if "error" in user_update_response:
        message = "Error During Update: " + user_update_response
    else:
        message = "User Updated!"

    return redirect(
        url_for(
            "ecommerce_views_bp.ecommerce_profile",
            _external="True",
            _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"],
            user_id=user_id,
            message=message))


# EMail user and admin when a new user registers successfully
def ecommerce_email_registration(recipient, token):
    logger.debug("ecommerce_email_registration()")
    app_title = session[SESSION_INSTANCE_SETTINGS_KEY]["settings"]["app_name"]
    activation_link = url_for(
        "gbac_registration_bp.gbac_registration_state_get",
        stateToken=token,
        _external=True,
        _scheme=session[SESSION_INSTANCE_SETTINGS_KEY]["app_scheme"])
    subject = "Welcome to the {app_title}".format(app_title=session[SESSION_INSTANCE_SETTINGS_KEY]["settings"]["app_name"])

    message = """
        Thank you for Applying for {app_title}! <br /> <br />Click this link to activate your account. <br /><br />
        <a href='{activation_link}'>Click Here to Activate Account</a>
        """.format(app_title=app_title, activation_link=activation_link)
    test = Email.send_mail(subject=subject, message=message, recipients=[recipient])
    logger.debug(test)


def safe_get_dict(mydict, key):
    myval = ""
    mydictval = mydict.get(key)
    if mydictval:
        if mydictval.strip() != "":
            myval = mydictval.strip()
    return myval
