# -*- coding: utf-8 -*-
# © 2015 Eficent Business and IT Consulting Services S.L. -
# Jordi Ballester Alomar
# © 2015 Serpent Consulting Services Pvt. Ltd. - Sudhir Arya
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openerp import netsvc
from openerp.tests import common


class TestSaleOperatingUnit(common.TransactionCase):

    def setUp(self):
        super(TestSaleOperatingUnit, self).setUp()
        self.res_groups = self.env['res.groups']
        self.partner_model = self.env['res.partner']
        self.res_users_model = self.env['res.users']
        self.sale_model = self.env['sale.order']
        self.sale_order_model = self.env['sale.order.line']
        self.acc_move_model = self.env['account.move']
        self.acc_invoice_model = self.env['account.invoice']
        self.res_company_model = self.env['res.company']
        self.product_model = self.env['product.product']
        self.operating_unit_model = self.env['operating.unit']
        self.company_model = self.env['res.company']
        self.payment_model = self.env['sale.advance.payment.inv']
        # Company
        self.company = self.env.ref('base.main_company')
        self.grp_sale_user = self.env.ref('base.group_sale_manager')
        self.grp_acc_user = self.env.ref('account.group_account_invoice')
        # Main Operating Unit
        self.ou1 = self.env.ref('operating_unit.main_operating_unit')
        # B2B Operating Unit
        self.b2b = self.env.ref('operating_unit.b2b_operating_unit')
        # B2C Operating Unit
        self.b2c = self.env.ref('operating_unit.b2c_operating_unit')
        # Payment Term
        self.pay = self.env.ref('account.account_payment_term_immediate')
        # Customer
        self.customer = self.env.ref('base.res_partner_2')
        # Price list
        self.pricelist = self.env.ref('product.list0')
        # Partner
        self.partner1 = self.env.ref('base.res_partner_1')
        # Products
        self.product1 = self.env.ref('product.product_product_7')
        # Create user1
        self.user1 = self._create_user('user_1', [self.grp_sale_user,
                                                  self.grp_acc_user],
                                       self.company, [self.ou1, self.b2c])
        # Create user2
        self.user2 = self._create_user('user_2', [self.grp_sale_user,
                                                  self.grp_acc_user],
                                       self.company, [self.b2c])
        # Create Sale Order1
        self.sale1 = self._create_sale_order(self.user1.id, self.customer,
                                             self.product1, self.pricelist,
                                             self.ou1)
        # Create Sale Order2
        self.sale2 = self._create_sale_order(self.user2.id, self.customer,
                                             self.product1, self.pricelist,
                                             self.b2c)

    def _create_user(self, login, groups, company, operating_units,
                     context=None):
        """Create a user."""
        group_ids = [group.id for group in groups]
        user = self.res_users_model.create({
            'name': 'Test Sales User',
            'login': login,
            'password': 'demo',
            'email': 'example@yourcompany.com',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'operating_unit_ids': [(4, ou.id) for ou in operating_units],
            'groups_id': [(6, 0, group_ids)]
        })
        return user

    def _create_sale_order(self, uid, customer, product, pricelist,
                           operating_unit):
        """Create a sale order."""
        sale = self.sale_model.sudo(uid).create({
            'partner_id': customer.id,
            'partner_invoice_id': customer.id,
            'partner_shipping_id': customer.id,
            'pricelist_id': pricelist.id,
            'operating_unit_id': operating_unit.id
        })
        self.sale_order_model.sudo(uid).create({
            'order_id': sale.id,
            'product_id': product.id,
            'name': 'Sale Order Line'
        })
        return sale

    def _confirm_sale(self, sale):
        sale.action_button_confirm()
        payment = self.payment_model.create({
            'advance_payment_method': 'all'
        })
        sale_context = {
            'active_id': sale.id,
            'active_ids': sale.ids,
            'active_model': 'sale.order',
            'open_invoices': True,
        }
        res = payment.with_context(sale_context).create_invoices()
        invoice_id = res['res_id']
        return invoice_id

    def test_security(self):
        """Test Sale Operating Unit"""
        # User 2 is only assigned to Operating Unit B2C, and cannot
        # Access Sales order from Main Operating Unit.
        sale = self.sale_model.sudo(self.user2.id).search(
                                          [('id', '=', self.sale1.id),
                                           ('operating_unit_id', '=',
                                           self.ou1.id)])
        self.assertEqual(sale.ids, [], 'User 2 should not have access to '
                                       'OU %s' % self.ou1.name)
        # Confirm Sale1
        self._confirm_sale(self.sale1)
        # Confirm Sale2
        b2c_invoice_id = self._confirm_sale(self.sale2)
        # Checks that invoice has OU b2c
        b2c = self.acc_invoice_model.sudo(self.user2.id).search(
                                         [('id', '=', b2c_invoice_id),
                                          ('operating_unit_id', '=',
                                           self.b2c.id)])
        self.assertNotEqual(b2c.ids, [], 'Invoice should have b2c OU')
