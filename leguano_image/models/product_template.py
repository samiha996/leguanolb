# addons/your_module/models/product_template.py
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    image_secondary = fields.Image(
        string="Second Image",
        max_width=1920,
        max_height=1920,
        help="An additional product image."
    )
