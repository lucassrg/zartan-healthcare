variable "org_name" {}
variable "api_token" {}
variable "base_url" {}
variable "demo_app_name" { default = "healthcare" }
variable "udp_subdomain" { default = "local_zartan" }

locals {
  app_domain       = "${var.udp_subdomain}.${var.demo_app_name}.unidemo.info"
  nodash_subdomain = replace(var.udp_subdomain, "-", "_")
}

terraform {
  required_providers {
    okta = {
      source = "okta/okta"
      version = "~> 3.19"
    }
  }
}
provider "okta" {
  org_name  = var.org_name
  api_token = var.api_token
  base_url  = var.base_url
}

data "okta_group" "all" {
  name = "Everyone"
}

resource "okta_trusted_origin" "local8666" {
  name   = "local-8666"
  origin = "http://localhost:8666"
  scopes = ["CORS", "REDIRECT"]
}

resource "okta_trusted_origin" "lgatkohealth_herokuapp" {
  name   = "lg-atko-health-herokuapp"
  origin = "https://lg-atko-health.herokuapp.com"
  scopes = ["CORS", "REDIRECT"]
}

resource "okta_trusted_origin" "atkohealth_herokuapp" {
  name   = "atko-health-herokuapp"
  origin = "https://atko-health.herokuapp.com"
  scopes = ["CORS", "REDIRECT"]
}

# resource "okta_app_oauth" "healthcare" {
#   label       = "${var.udp_subdomain} ${var.demo_app_name}"
#   type        = "web"
#   grant_types = ["authorization_code"]
#   redirect_uris = [
#     "https://${local.app_domain}/authorization-code/callback",
#     "http://localhost:8666/authorization-code/callback"
#   ]
#   response_types = ["code"]
#   issuer_mode    = "ORG_URL"
# }

# resource "okta_app_group_assignment" "healthcare_app_group" {
#   app_id   = okta_app_oauth.healthcare.id
#   group_id = data.okta_group.all.id
# #   profile = <<JSON
# # {
# #   "<app_profile_field>": "<value>"
# # }
# # JSON
# }

# resource "okta_trusted_origin" "healthcare_https" {
#   name   = "${var.udp_subdomain} ${var.demo_app_name} HTTPS"
#   origin = "https://${local.app_domain}"
#   scopes = ["REDIRECT", "CORS"]
# }
# resource "okta_auth_server_policy_rule" "healthcare" {
#   auth_server_id       = okta_auth_server.healthcare.id
#   policy_id            = okta_auth_server_policy.healthcare.id
#   status               = "ACTIVE"
#   name                 = "one_hour"
#   priority             = 1
#   group_whitelist      = ["${data.okta_group.all.id}"]
#   grant_type_whitelist = ["authorization_code", "implicit"]
#   scope_whitelist      = ["*"]
# }

resource "okta_group" "patients_with_consent" {
  name        = "PatientsWithConsent"
  description = "Group of Patient users With Consent"
}

resource "okta_group" "patients_without_consent" {
  name        = "PatientsWithoutConsent"
  description = "Group of Patient users Without Consent"
}

resource "okta_group_rule" "patients_with_consent" {
  name              = "PatientsWithConsent"
  status            = "ACTIVE"
  group_assignments = [okta_group.patients_with_consent.id]
  expression_type   = "urn:okta:expression:1.0"
  expression_value  = "String.len(String.removeSpaces(${var.udp_subdomain}_${var.demo_app_name}_consent)) > 0"
}

resource "okta_group_rule" "patients_without_consent" {
  name              = "PatientsWithoutConsent"
  status            = "ACTIVE"
  group_assignments = [okta_group.patients_without_consent.id]
  expression_type   = "urn:okta:expression:1.0"
  expression_value  = "String.len(String.removeSpaces(${var.udp_subdomain}_${var.demo_app_name}_consent)) == 0"
}


data "okta_app" "atko_health_web" {
  label = "Atko-health-web"
  active_only = true
}

data "okta_app" "atko_health_spa" {
  label = "Atko-health-SPA"
  active_only = true
}



resource "okta_app_group_assignments" "atko_health_web_group_assignments" {
  app_id   = data.okta_app.atko_health_web.id

  group {
    id = okta_group.patients_with_consent.id    
  }
  group {
    id = okta_group.patients_without_consent.id
  }
}

resource "okta_app_group_assignments" "atko_health_spa_group_assignments" {
  app_id   = data.okta_app.atko_health_spa.id

  group {
    id = okta_group.patients_with_consent.id
  }
  group {
    id = okta_group.patients_without_consent.id
  }
}


resource "okta_auth_server" "healthcare" {
  name        = "${var.udp_subdomain} ${var.demo_app_name}"
  description = "Atko-health"
  audiences   = ["api://${local.app_domain}"]
}

resource "okta_auth_server_policy" "healthcare" {
  auth_server_id   = okta_auth_server.healthcare.id
  status           = "ACTIVE"
  name             = "standard"
  description      = "Atko-health"
  priority         = 1
  client_whitelist = [data.okta_app.atko_health_web.id, data.okta_app.atko_health_spa.id]
}

resource "okta_auth_server_policy_rule" "auth_default_policy_rule" {
  auth_server_id   = okta_auth_server.healthcare.id
  policy_id            = okta_auth_server_policy.healthcare.id
  status               = "ACTIVE"
  name                 = "healthcare_default"
  priority             = 1
  # group_whitelist      = [okta_group.patients_with_consent.id, okta_group.patients_without_consent.id]
  group_whitelist = ["EVERYONE"]
  grant_type_whitelist = ["implicit", "authorization_code"]
  scope_whitelist = ["*"]
  access_token_lifetime_minutes = 60
}



# resource "okta_policy_signon" "patient" {
#   name            = "patient"
#   status          = "ACTIVE"
#   description     = "Patients sign-on policy"
#   groups_included = ["${data.okta_group.everyone.id}"]
# }



resource "okta_user_schema_property" "customfield1" {
  index       = "${local.nodash_subdomain}_${var.demo_app_name}_last_verified_date"
  title       = "${var.udp_subdomain}_${var.demo_app_name}_last_verified_date"
  type        = "string"
  description = "Date Evident Last Verified"
  master      = "OKTA"
  scope       = "SELF"
  permissions = "READ_WRITE"
}

resource "okta_user_schema_property" "customfield2" {
  index       = "${local.nodash_subdomain}_${var.demo_app_name}_evident_id"
  title       = "${var.udp_subdomain}_${var.demo_app_name}_evident_id"
  type        = "string"
  description = "Evident ID"
  master      = "OKTA"
  scope       = "SELF"
  permissions = "READ_WRITE"
  depends_on  = [okta_user_schema_property.customfield1]
}

resource "okta_user_schema_property" "customfield3" {
  index       = "${local.nodash_subdomain}_${var.demo_app_name}_dob"
  title       = "${var.udp_subdomain}_${var.demo_app_name}_dob"
  type        = "string"
  description = "Date of Birth"
  master      = "OKTA"
  scope       = "SELF"
  permissions = "READ_WRITE"
  depends_on  = [okta_user_schema_property.customfield2]
}

resource "okta_user_schema_property" "customfield4" {
  index       = "${local.nodash_subdomain}_${var.demo_app_name}_gender"
  title       = "${var.udp_subdomain}_${var.demo_app_name}_gender"
  type        = "string"
  description = "Gender"
  master      = "OKTA"
  scope       = "SELF"
  permissions = "READ_WRITE"
  depends_on  = [okta_user_schema_property.customfield3]
}

resource "okta_user_schema_property" "customfield5" {
  index       = "${local.nodash_subdomain}_${var.demo_app_name}_hasvisited"
  title       = "${var.udp_subdomain}_${var.demo_app_name}_hasvisited"
  type        = "string"
  description = "Patient has visited facility"
  master      = "OKTA"
  scope       = "SELF"
  permissions = "READ_WRITE"
  depends_on  = [okta_user_schema_property.customfield4]
}

resource "okta_user_schema_property" "customfield6" {
  index       = "${local.nodash_subdomain}_${var.demo_app_name}_consent"
  title       = "${var.udp_subdomain}_${var.demo_app_name}_consent"
  type        = "string"
  description = "Date Patient Consented HIPAA"
  master      = "OKTA"
  scope       = "SELF"
  permissions = "READ_WRITE"
  depends_on  = [okta_user_schema_property.customfield5]
}




# output "client_id" {
#   value = "${okta_app_oauth.healthcare.client_id}"
# }
# output "client_secret" {
#   value = "${okta_app_oauth.healthcare.client_secret}"
# }
# output "domain" {
#   value = "${var.org_name}.${var.base_url}"
# }
# output "auth_server_id" {
#   value = "${okta_auth_server.healthcare.id}"
# }
# output "issuer" {
#   value = "${okta_auth_server.healthcare.issuer}"
# }
# output "okta_app_oauth_id" {
#   value = "${okta_app_oauth.healthcare.id}"
# }
