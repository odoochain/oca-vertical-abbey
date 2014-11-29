# -*- encoding: utf-8 -*-
##############################################################################
#
#    Stay module for Odoo
#    Copyright (C) 2014 Artisanat Monastique de Provence
#                  (http://www.barroux.org)
#    @author: Alexis de Lattre <alexis.delattre@akretion.com>
#    @author: Brother Bernard <informatique@barroux.org>
#    @author: Brother Irénée
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
from openerp.exceptions import Warning
from datetime import datetime
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


class StayJournalPrint(models.TransientModel):
    _name = 'stay.journal.print'
    _description = 'Print the Stay Lines'
    _rec_name = 'date'

    @api.model
    def _default_date(self):
        today_str = fields.Date.context_today(self)
        today_dt = datetime.strptime(today_str, DEFAULT_SERVER_DATE_FORMAT)
        return today_dt + relativedelta(days=1)

    date = fields.Date(string='Date', required=True, default=_default_date)

    @api.multi
    def print_journal(self):
        assert len(self) == 1, 'Only one recordset allowed'
        self = self[0]
        lines = self.env['stay.line'].search([
            ('date', '=', self.date),
            ('company_id', '=', self.env.user.company_id.id),
            ])
        if not lines:
            raise Warning(_('No stay for this date.'))
        data = {'form': {'date': self.date}}
        res = self.env['report'].get_action(
            self.env['report'].browse(False), 'stay.report_stay_journal',
            data=data)
        return res
