variable "org_name" {}
variable "api_token" {}
variable "base_url" {}
variable "demo_app_name" {}
variable "udp_subdomain" {}
variable "test_app_domain" {}

locals {
    app_url = "${var.test_app_domain}"
}

provider "okta" {
  org_name  = "${var.org_name}"
  api_token = "${var.api_token}"
  base_url  = "${var.base_url}"
  version   = "~> 3.0"
}
provider "template" {
  version = "~> 2.1"
}
provider "local" {
  version = "~> 1.2"
}
data "okta_group" "all" {
  name = "Everyone"
}
resource "okta_app_oauth" "hospitality" {
  label          = "${var.udp_subdomain} ${var.demo_app_name} Demo (Generated by UDP)"
  type           = "web"
  grant_types    = ["authorization_code"]
  redirect_uris  = ["https://${local.app_url}/authorization-code/callback"]
  response_types = ["code"]
  issuer_mode    = "ORG_URL"
  consent_method = "TRUSTED"
  groups         = ["${data.okta_group.all.id}"]
}
resource "okta_trusted_origin" "hospitality" {
  name   = "${local.app_url}"
  origin = "https://${local.app_url}"
  scopes = ["REDIRECT", "CORS"]
}
resource "okta_auth_server" "hospitality" {
  name        = "${var.udp_subdomain} ${var.demo_app_name}"
  description = "Generated by UDP"
  audiences   = ["api://${local.app_url}"]
}
resource "okta_auth_server_policy" "hospitality" {
  auth_server_id   = "${okta_auth_server.hospitality.id}"
  status           = "ACTIVE"
  name             = "standard"
  description      = "Generated by UDP"
  priority         = 1
  client_whitelist = ["${okta_app_oauth.hospitality.id}"]
}
resource "okta_auth_server_policy_rule" "hospitality" {
  auth_server_id       = "${okta_auth_server.hospitality.id}"
  policy_id            = "${okta_auth_server_policy.hospitality.id}"
  status               = "ACTIVE"
  name                 = "one_hour"
  priority             = 1
  group_whitelist      = ["${data.okta_group.all.id}"]
  grant_type_whitelist = ["authorization_code"]
  scope_whitelist      = ["*"]
}
data "template_file" "configuration" {
  template = "${file("${path.module}/hospitality.dotenv.template")}"
  vars = {
    client_id         = "${okta_app_oauth.hospitality.client_id}"
    client_secret     = "${okta_app_oauth.hospitality.client_secret}"
    domain            = "${var.org_name}.${var.base_url}"
    auth_server_id    = "${okta_auth_server.hospitality.id}"
    issuer            = "${okta_auth_server.hospitality.issuer}"
    okta_app_oauth_id = "${okta_app_oauth.hospitality.id}"
  }
}
resource "local_file" "dotenv" {
  content  = "${data.template_file.configuration.rendered}"
  filename = "${path.module}/hospitality.env"
}