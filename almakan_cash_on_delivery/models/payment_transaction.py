# -*- coding: utf-8 -*-
from odoo import api, models

class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _maybe_autoconfirm_sale_orders(self):
        """Confirm related sale orders if the provider matches our allowlist."""
        ICP = self.env["ir.config_parameter"].sudo()
        enabled = ICP.get_param("sale_wire_autoconfirm.enable", "True").strip().lower() in {"1", "true", "yes"}
        if not enabled:
            return

        # Comma-separated tokens checked against several provider fields
        # Defaults cover:
        #  - Odoo built-in bank transfer provider code: 'transfer'
        #  - common aliases you might use in custom providers
        default_tokens = "transfer,wire,bank transfer,bank_transfer,wire_transfer"
        tokens = {
            t.strip().lower()
            for t in ICP.get_param("sale_wire_autoconfirm.providers", default_tokens).split(",")
            if t.strip()
        }

        for tx in self:
            # Probe multiple fields to be version-safe:
            # - provider_code: new-style (payment.provider linkage)
            # - acquirer_id.provider: older-style
            # - provider_id.custom_mode/name: for custom providers
            probe_values = []

            provider_code = getattr(tx, "provider_code", False)
            if provider_code:
                probe_values.append(str(provider_code).lower())

            acq = getattr(tx, "acquirer_id", False)
            if acq:
                if getattr(acq, "provider", False):
                    probe_values.append(str(acq.provider).lower())
                if getattr(acq, "name", False):
                    probe_values.append(str(acq.name).lower())

            prov = getattr(tx, "provider_id", False)
            if prov:
                # custom providers often expose custom_mode or name
                for attr in ("custom_mode", "code", "name"):
                    val = getattr(prov, attr, False)
                    if val:
                        probe_values.append(str(val).lower())

            if not (set(probe_values) & tokens):
                continue

            sale_orders = getattr(tx, "sale_order_ids", self.env["sale.order"])
            # Confirm only quotations / sent quotations
            for so in sale_orders.filtered(lambda o: o.state in ("draft", "sent")):
                # action_confirm will also handle stock reservations etc.
                so.action_confirm()

    @api.model_create_multi
    def create(self, vals_list):
        """Run once on creation in case your flow creates a pending tx immediately."""
        txs = super().create(vals_list)
        txs._maybe_autoconfirm_sale_orders()
        return txs

    def _set_pending(self):
        """Hook when transactions are put in 'pending' (typical for wire transfer)."""
        res = super()._set_pending()
        self._maybe_autoconfirm_sale_orders()
        return res
