# -*- coding: utf-8 -*-
# © 2014-2017 Barroux Abbey (www.barroux.org)
# © 2014-2017 Akretion France (www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# @author: Brother Bernard <informatique@barroux.org>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    mass_validation_account_id = fields.Many2one(
        'account.account', string='Mass Validation Account',
        domain=[('deprecated', '!=', True)])
    mass_validation_journal_id = fields.Many2one(
        'account.journal', string='Mass Validation Journal')
    mass_post_move = fields.Boolean(string='Post Move', default=True)
