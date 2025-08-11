# Copyright 2023 Jarsa
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_partner_pricelist = fields.Boolean(
        related="company_id.use_partner_pricelist",
        readonly=False,
    )

    @api.onchange("use_partner_pricelist")
    def _onchange_use_partner_pricelist(self):
        if self.use_partner_pricelist and not self.group_product_pricelist:
            self.group_product_pricelist = True
