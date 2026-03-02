# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo.tools.sql import column_exists, create_column

_logger = logging.getLogger(__name__)

COLUMNS = (
    ("sale_order", "price_subtotal_no_discount"),
    ("sale_order", "price_total_no_discount"),
    ("sale_order", "discount_total"),
    ("sale_order_line", "price_subtotal_no_discount"),
    ("sale_order_line", "price_total_no_discount"),
    ("sale_order_line", "discount_total"),
    ("sale_order_line", "discount_subtotal"),
)


def pre_init_hook(env):
    cr = env.cr  # Retrieve the database cursor
    for table, column in COLUMNS:
        if not column_exists(cr, table, column):
            _logger.info("Create discount column %s in database", column)
            create_column(cr, table, column, "numeric")

def post_init_hook(env):
    cr = env.cr  # Retrieve the database cursor
    _logger.info("Starting post_init_hook for sale_discount_display_amount")

    # Lines WITHOUT discount: trivial SQL
    _logger.info("Initializing non-discount lines via SQL...")
    cr.execute("""
        UPDATE sale_order_line
        SET price_subtotal_no_discount = price_subtotal,
            price_total_no_discount = price_total,
            discount_total = 0.0,
            discount_subtotal = 0.0
        WHERE (discount = 0.0 OR discount IS NULL)
    """)

    # Lines WITH discount:
    #   price_subtotal_no_discount = price_unit * product_uom_qty  (exact: no discount applied)
    #   price_total_no_discount    = subtotal_no_discount * (price_total / price_subtotal)
    #                                (approximation: assumes proportional taxes)
    #   discount_subtotal / discount_total = difference vs actual subtotal/total
    _logger.info("Initializing discount lines via SQL...")
    cr.execute("""
        UPDATE sale_order_line
        SET price_subtotal_no_discount = price_unit * product_uom_qty,
            discount_subtotal          = (price_unit * product_uom_qty) - price_subtotal,
            price_total_no_discount    = CASE
                                            WHEN price_subtotal != 0
                                            THEN (price_unit * product_uom_qty) * price_total / price_subtotal
                                            ELSE price_unit * product_uom_qty
                                         END,
            discount_total             = CASE
                                            WHEN price_subtotal != 0
                                            THEN (price_unit * product_uom_qty) * price_total / price_subtotal - price_total
                                            ELSE 0.0
                                         END
        WHERE discount > 0.0
    """)

    # sale_order totals: sum of lines
    _logger.info("Updating sale_order totals...")
    cr.execute("""
        UPDATE sale_order so
        SET price_subtotal_no_discount = COALESCE((
                SELECT SUM(sol.price_subtotal_no_discount)
                FROM sale_order_line sol
                WHERE sol.order_id = so.id
            ), 0.0),
            price_total_no_discount = COALESCE((
                SELECT SUM(sol.price_total_no_discount)
                FROM sale_order_line sol
                WHERE sol.order_id = so.id
            ), 0.0),
            discount_total = COALESCE((
                SELECT SUM(sol.discount_total)
                FROM sale_order_line sol
                WHERE sol.order_id = so.id
            ), 0.0)
    """)

    _logger.info("post_init_hook finished successfully")

