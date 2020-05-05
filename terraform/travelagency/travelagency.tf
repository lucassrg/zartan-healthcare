variable "org_name" {}
variable "api_token" {}
variable "base_url" {}
variable "demo_app_name" {}
variable "udp_subdomain" {}

terraform {
  backend "s3" {
  }
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
resource "okta_app_oauth" "travelagency" {
  label          = "${var.udp_subdomain} ${var.demo_app_name} Demo (Generated by UDP)"
  type           = "web"
  grant_types    = ["authorization_code"]
  redirect_uris  = ["https://${var.udp_subdomain}.${var.demo_app_name}.unidemo.info/authorization-code/callback"]
  response_types = ["code"]
  issuer_mode    = "ORG_URL"
}
resource "okta_trusted_origin" "travelagency" {
  name   = "${var.udp_subdomain}.${var.demo_app_name}.unidemo.info"
  origin = "https://${var.udp_subdomain}.${var.demo_app_name}.unidemo.info"
  scopes = ["REDIRECT", "CORS"]
}
resource "okta_auth_server" "travelagency" {
  name        = "${var.udp_subdomain} ${var.demo_app_name}"
  description = "Generated by UDP"
  audiences   = ["api://travelagency.unidemo"]
}
resource "okta_auth_server_policy" "travelagency" {
  auth_server_id   = "${okta_auth_server.travelagency.id}"
  status           = "ACTIVE"
  name             = "standard"
  description      = "Generated by UDP"
  priority         = 1
  client_whitelist = ["${okta_app_oauth.travelagency.id}"]
}
data "okta_group" "all" {
  name = "Everyone"
}
resource "okta_auth_server_policy_rule" "travelagency" {
  auth_server_id       = "${okta_auth_server.travelagency.id}"
  policy_id            = "${okta_auth_server_policy.travelagency.id}"
  status               = "ACTIVE"
  name                 = "one_hour"
  priority             = 1
  grant_type_whitelist = ["authorization_code"]
  scope_whitelist      = ["*"]
}
data "template_file" "configuration" {
  template = "${file("${path.module}/travelagency.dotenv.template")}"
  vars = {
    client_id         = "${okta_app_oauth.travelagency.client_id}"
    client_secret     = "${okta_app_oauth.travelagency.client_secret}"
    domain            = "${var.org_name}.${var.base_url}"
    auth_server_id    = "${okta_auth_server.travelagency.id}"
    issuer            = "${okta_auth_server.travelagency.issuer}"
    okta_app_oauth_id = "${okta_app_oauth.travelagency.id}"
  }
}
resource "local_file" "dotenv" {
  content  = "${data.template_file.configuration.rendered}"
  filename = "${path.module}/travelagency.env"
}