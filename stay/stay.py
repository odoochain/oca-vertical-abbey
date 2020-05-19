# -*- coding: utf-8 -*-
# © 2014-2017 Barroux Abbey (www.barroux.org)
# © 2014-2017 Akretion France (www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# @author: Brother Bernard <informatique@barroux.org>
# @author: Brother Irénée
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StayStay(models.Model):
    _name = 'stay.stay'
    _description = 'Guest Stay'
    _order = 'arrival_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Stay Number', default='/', copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'stay.stay'))
    partner_id = fields.Many2one(
        'res.partner', string='Guest', ondelete='restrict',
        help="If guest is anonymous, leave this field empty.")
    partner_name = fields.Char(
        'Guest Name', required=True, track_visibility='onchange')
    guest_qty = fields.Integer(
        string='Guest Quantity', default=1, track_visibility='onchange')
    arrival_date = fields.Date(
        string='Arrival Date', required=True, track_visibility='onchange')
    arrival_time = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ], string='Arrival Time', required=True, track_visibility='onchange')
    departure_date = fields.Date(
        string='Departure Date', required=True, track_visibility='onchange')
    departure_time = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ], string='Departure Time', required=True, track_visibility='onchange')
    room_id = fields.Many2one(
        'stay.room', string='Room', track_visibility='onchange', copy=False,
        ondelete='restrict')
    # Here, group_id is not a related of room, because we want to be able
    # to first set the group and later set the room
    group_id = fields.Many2one(
        'stay.group', string='Group', track_visibility='onchange', copy=False)
    user_id = fields.Many2one(
        related='group_id.user_id', store=True, readonly=True)
    line_ids = fields.One2many(
        'stay.line', 'stay_id', string='Stay Lines')
    no_meals = fields.Boolean(
        string="No Meals",
        help="The stay lines generated from this stay will not have "
        "lunchs nor dinners by default.")
    calendar_display_name = fields.Char(
        compute='_compute_calendar_display_name', store=True)

    _sql_constraints = [(
        'name_company_uniq', 'unique(name, company_id)',
        'A stay with this number already exists for this company.')]

    @api.model
    def create(self, vals=None):
        if vals is None:
            vals = {}
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('stay.stay')
        return super(StayStay, self).create(vals)

    @api.depends('partner_name', 'arrival_time', 'departure_time', 'room_id')
    def _compute_calendar_display_name(self):
        time2code = {
            'morning': _('Mo'),
            'afternoon': _('Af'),
            'evening': _('Ev'),
            }
        for stay in self:
            if stay.room_id:
                room = stay.room_id.code or stay.room_id.name
            else:
                room = _('No Room')
            stay.calendar_display_name = u'[%s] %s, %s, %d [%s]' % (
                time2code[stay.arrival_time],
                stay.partner_name,
                room,
                stay.guest_qty,
                time2code[stay.departure_time])

    @api.constrains('departure_date', 'arrival_date', 'room_id', 'group_id')
    def _check_stay(self):
        for stay in self:
            if stay.arrival_date >= stay.departure_date:
                raise ValidationError(_(
                    'Arrival date (%s) must be earlier than '
                    'departure date (%s)')
                    % (stay.arrival_date, stay.departure_date))
            if (
                    stay.room_id and
                    stay.room_id.group_id and
                    stay.group_id != stay.room_id.group_id):
                raise ValidationError(_(
                    "For stay '%s', the room '%s' is linked to "
                    "group '%s', but the selected group is '%s'.") % (
                        stay.display_name,
                        stay.room_id.display_name,
                        stay.room_id.group_id.display_name,
                        stay.group_id.display_name))
            if self.room_id and self.room_id.capacity == 1:
                stay._check_reservation_conflict_single()

    def _check_reservation_conflict_single(self):
        self.ensure_one()
        assert self.room_id
        # No conflict IF :
        # leaves before my arrival (or same day)
        # OR arrivers after my departure (or same day)
        # CONTRARY :
        # leaves after my arrival
        # AND arrives before my departure
        conflict_stay = self.search([
            ('id', '!=', self.id),
            ('room_id', '=', self.room_id.id),
            ('departure_date', '>', self.arrival_date),
            ('arrival_date', '<', self.departure_date),
            ], limit=1)
        if conflict_stay:
            raise ValidationError(_(
                "This stay conflicts with stay %s of '%s' "
                "from %s to %s in room %s.") % (
                    conflict_stay.name,
                    conflict_stay.partner_name,
                    conflict_stay.arrival_date,
                    conflict_stay.departure_date,
                    conflict_stay.room_id.display_name))

    @api.onchange('partner_id')
    def partner_id_change(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name

    @api.onchange('room_id')
    def room_id_change(self):
        if self.room_id:
            self.no_meals = self.room_id.no_meals
            if self.room_id.group_id:
                self.group_id = self.room_id.group_id.id

    @api.onchange('group_id')
    def group_id_change(self):
        res = {'domain': {'room_id': []}}
        if self.group_id and not self.room_id:
            res['domain']['room_id'] = [('group_id', '=', self.group_id.id)]
        return res


class StayRefectory(models.Model):
    _name = 'stay.refectory'
    _description = 'Refectory'
    _order = 'code, name'
    _rec_name = 'display_name'

    code = fields.Char(string='Code', size=10)
    name = fields.Char(string='Name', required=True)
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name_field',
        readonly=True, store=True)
    capacity = fields.Integer(string='Capacity')
    active = fields.Boolean(default=True)

    _sql_constraints = [(
        'code_uniq', 'unique(code)',
        'A refectory with this code already exists.')]

    @api.depends('name', 'code')
    def _compute_display_name_field(self):
        for ref in self:
            name = ref.name
            if ref.code:
                name = u'[%s] %s' % (ref.code, name)
            ref.display_name = name


class StayRoom(models.Model):
    _name = 'stay.room'
    _description = 'Room'
    _order = 'sequence, code'
    _rec_name = 'display_name'

    code = fields.Char(string='Code', size=10, copy=False)
    name = fields.Char(string='Name', required=True, copy=False)
    sequence = fields.Integer()
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name_field',
        readonly=True, store=True)
    group_id = fields.Many2one('stay.group', string='Group')
    user_id = fields.Many2one(
        related='group_id.user_id', store=True, readonly=True)
    bed_qty = fields.Integer(string='Number of beds', default=1)
    active = fields.Boolean(default=True)
    no_meals = fields.Boolean(
        string="No Meals",
        help="If active, the stays linked to this room will have the "
        "same option active by default.")

    _sql_constraints = [(
        'code_uniq', 'unique(code)',
        'A room with this code already exists.')]

    @api.depends('name', 'code')
    def _compute_display_name_field(self):
        for room in self:
            name = room.name
            if room.code:
                name = u'[%s] %s' % (room.code, name)
            room.display_name = name


class StayGroup(models.Model):
    _name = 'stay.group'
    _description = 'Stay Group'
    _order = 'sequence, id'

    name = fields.Char(string='Group Name', required=True)
    user_id = fields.Many2one('res.users', string='In Charge')
    sequence = fields.Integer()
    room_ids = fields.One2many(
        'stay.room', 'group_id', string='Rooms')

    _sql_constraints = [(
        'name_uniq', 'unique(name)',
        'A group with this name already exists.')]


class StayLine(models.Model):
    _name = 'stay.line'
    _description = 'Stay Journal'
    _rec_name = 'partner_name'
    _order = 'date desc'

    @api.model
    def _default_refectory(self):
        company = self.env['res.company']._company_default_get(
            'stay.line')
        return company.default_refectory_id

    stay_id = fields.Many2one('stay.stay', string='Stay')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self:
        self.env['res.company']._company_default_get('stay.line'))
    date = fields.Date(
        string='Date', required=True, default=fields.Date.context_today)
    lunch_qty = fields.Integer(string='Lunches')
    dinner_qty = fields.Integer(string='Dinners')
    bed_night_qty = fields.Integer(string='Bed Nights')
    partner_id = fields.Many2one(
        'res.partner', string='Guest',
        help="If guest is anonymous, leave this field empty.")
    partner_name = fields.Char('Guest Name', required=True)
    refectory_id = fields.Many2one(
        'stay.refectory', string='Refectory', default=_default_refectory)
    room_id = fields.Many2one('stay.room', string='Room', ondelete='restrict')
    group_id = fields.Many2one(
        related='room_id.group_id', store=True, readonly=True)
    user_id = fields.Many2one(
        related='room_id.group_id.user_id', store=True, readonly=True)

    @api.constrains(
        'refectory_id', 'lunch_qty', 'dinner_qty', 'date', 'room_id')
    def _check_room_refectory(self):
        for line in self:
            if (line.lunch_qty or line.dinner_qty) and not line.refectory_id:
                raise ValidationError(
                    _("Missing refectory for guest '%s' on %s.")
                    % (line.partner_name, line.date))
            if line.room_id and line.bed_night_qty:
                same_room_same_day_line = self.search([
                    ('date', '=', line.date),
                    ('room_id', '=', line.room_id.id),
                    ('bed_night_qty', '!=', False)])
                guests_in_room_qty = 0
                for same_room in same_room_same_day_line:
                    guests_in_room_qty += same_room.bed_night_qty
                if guests_in_room_qty > line.room_id.bed_qty:
                    raise ValidationError(_(
                        "The room '%s' is booked or all beds of the "
                        "room are booked")
                        % line.room_id.name)

    _sql_constraints = [
        ('lunch_qty_positive', 'CHECK (lunch_qty >= 0)',
            'The number of lunches must be positive or null'),
        ('dinner_qty_positive', 'CHECK (dinner_qty >= 0)',
            'The number of dinners must be positive or null'),
        ('bed_night_qty_positive', 'CHECK (bed_night_qty >= 0)',
            'The number of bed nights must be positive or null'),
    ]

    @api.onchange('partner_id')
    def _partner_id_change(self):
        if self.partner_id:
            self.partner_name = self.partner_id.display_name


class StayDateLabel(models.Model):
    _name = 'stay.date.label'
    _description = 'Stay Date Label'
    _order = 'date desc'

    date = fields.Date(required=True)
    name = fields.Char(string='Label')

    _sql_constraints = [(
        'date_uniq', 'unique(date)', 'This date already exists')]
