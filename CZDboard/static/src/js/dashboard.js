/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc"; 
import { Component, useState, onWillStart, onMounted, useEffect } from "@odoo/owl";

export class CZDboard extends Component {
    static template = "CZDboard.MainTemplate";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.activeCharts = {};

        this.state = useState({
            loading: false,
            hasData: false, 
            showCustomDate: false,
            filterOptions: { cities: [], companies: [], branches: [] },
            selected: {
                city_ids: [],
                company_ids: [],
                branch_ids: [],
                date_from: this._getFormattedDate(new Date(new Date().getFullYear(), new Date().getMonth(), 1)),
                date_to: this._getFormattedDate(new Date())
            },
            stats: [],
            excluded_sources: [], 
            activeSalesTab: 'all',
        });

        onWillStart(async () => {
            await loadJS("https://cdn.jsdelivr.net/npm/apexcharts");
        });

        useEffect(() => {
            if (window.ApexCharts && this.state.hasData && !this.state.loading && this.state.stats.length > 0) {
                const timer = setTimeout(() => {
                    this._renderAllCharts();
                }, 400);
                return () => clearTimeout(timer);
            }
        }, () => [this.state.stats, this.state.activeSalesTab, this.state.excluded_sources]);

        onMounted(async () => {
            await this._loadInitialFilters();
        });
    }

    _getFormattedDate(date) { 
        return date.toISOString().split('T')[0]; 
    }

    getSafeId(prefix, name) {
        if (!name) return prefix + '_unknown';
        return prefix + '_' + name.toString().replace(/[^a-z0-9]/gi, '_').toLowerCase();
    }

    async onApplyFilters() {
        this.state.loading = true;
        this.state.hasData = false;

        const params = {
            city_ids: this.state.selected.city_ids.length > 0 ? this.state.selected.city_ids : null,
            company_ids: this.state.selected.company_ids.length > 0 ? this.state.selected.company_ids : null,
            branch_ids: this.state.selected.branch_ids.length > 0 ? this.state.selected.branch_ids : null,
            date_from: this.state.selected.date_from,
            date_to: this.state.selected.date_to
        };

        try {
            const [regResult, salesResult] = await Promise.all([
                rpc("/web/czdboard/get_crm_stats", params),
                rpc("/web/czdboard/get_sales_stats", params)
            ]);

            let finalStats = regResult.data || [];
            if (salesResult && salesResult.status === "ok") {
                finalStats.push({ is_sales_group: true, name: "Sales Sector", levels: salesResult.data });
            }
            this.state.stats = finalStats;
            this._recalculateTotals();
            this.state.hasData = true;
        } catch (error) {
            this.notification.add("Data fetch failed", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async _loadInitialFilters() {
        const result = await rpc("/web/czdboard/filters", {});
        if (result && result.status === "ok") {
            this.state.filterOptions.cities = result.data.cities;
            await this._updateCompanies();
            await this._updateBranches();
        }
    }

    async _updateCompanies() {
        const res = await rpc("/web/czdboard/get_companies_by_cities", { 
            city_ids: this.state.selected.city_ids.length > 0 ? this.state.selected.city_ids : null 
        });
        this.state.filterOptions.companies = res.data || [];
    }

    async _updateBranches() {
        const res = await rpc("/web/czdboard/get_branches_refined", { 
            city_ids: this.state.selected.city_ids.length > 0 ? this.state.selected.city_ids : null,
            company_ids: this.state.selected.company_ids.length > 0 ? this.state.selected.company_ids : null
        });
        this.state.filterOptions.branches = res.data || [];
    }

    changeSalesTab(tabId) { this.state.activeSalesTab = tabId; }

    toggleItem(fieldName, id, ev) {
        if (ev.target.checked) {
            if (!this.state.selected[fieldName].includes(id)) this.state.selected[fieldName].push(id);
        } else {
            const index = this.state.selected[fieldName].indexOf(id);
            if (index > -1) this.state.selected[fieldName].splice(index, 1);
        }
        if (fieldName === 'city_ids') this._updateCompanies();
        if (fieldName === 'company_ids') this._updateBranches();
    }

    toggleSourceExclusion(sourceName) {
        const idx = this.state.excluded_sources.indexOf(sourceName);
        if (idx > -1) this.state.excluded_sources.splice(idx, 1);
        else this.state.excluded_sources.push(sourceName);
        this._recalculateTotals();
    }

    onDatePresetChange(ev) {
        const val = ev.target.value;
        const now = new Date();
        this.state.showCustomDate = (val === 'custom'); 
        if (val === 'this_month') {
            this.state.selected.date_from = this._getFormattedDate(new Date(now.getFullYear(), now.getMonth(), 1));
            this.state.selected.date_to = this._getFormattedDate(now);
        } else if (val === 'last_month') {
            this.state.selected.date_from = this._getFormattedDate(new Date(now.getFullYear(), now.getMonth() - 1, 1));
            this.state.selected.date_to = this._getFormattedDate(new Date(now.getFullYear(), now.getMonth(), 0));
        }
    }

    _recalculateTotals() {
        this.state.stats.forEach(dept => {
            const process = (target) => {
                let t_untouched = 0, t_unreached = 0, t_reached = 0, t_booked = 0;
                target.sources.forEach(src => {
                    if (!this.state.excluded_sources.includes(src.name)) {
                        t_untouched += src.untouched; t_unreached += src.unreached;
                        t_reached += src.reached; t_booked += src.booked;
                    }
                });
                target.total_count = t_untouched + t_unreached + t_reached;
                target.total_untouched = t_untouched;
                target.total_reached = t_reached;
                target.total_booked = t_booked;
                target.avg_cr = t_reached > 0 ? ((t_booked / t_reached) * 100).toFixed(1) : 0;
                target.main_chart_data = [t_untouched, t_unreached, t_reached];
            };
            if (dept.is_sales_group) dept.levels.forEach(l => process(l));
            else process(dept);
        });
    }

    _renderAllCharts() {
        Object.values(this.activeCharts).forEach(c => c?.destroy?.());
        this.activeCharts = {}; 

        this.state.stats.forEach(dept => {
            if (dept.is_sales_group) {
                const level = dept.levels.find(l => l.id === this.state.activeSalesTab);
                if (level) {
                    const mId = this.getSafeId('main_chart', dept.name + level.id);
                    this.activeCharts[mId] = this._createDoughnut(mId, level.main_chart_data, true);
                    level.sources.forEach(s => {
                        const sId = this.getSafeId('chart_src', s.name + level.id);
                        this.activeCharts[sId] = this._createDoughnut(sId, [s.untouched, s.unreached, s.reached], false);
                    });
                }
            } else {
                const mId = this.getSafeId('main_chart', dept.name);
                this.activeCharts[mId] = this._createDoughnut(mId, dept.main_chart_data, true);
                dept.sources.forEach(s => {
                    const sId = this.getSafeId('chart_src', s.name);
                    this.activeCharts[sId] = this._createDoughnut(sId, [s.untouched, s.unreached, s.reached], false);
                });
            }
        });
    }

    _createDoughnut(elId, data, isMain = false) {
        const el = document.getElementById(elId);
        if (!el || !window.ApexCharts) return null;
        const options = {
            series: data || [0, 0, 0],
            chart: { type: 'donut', height: isMain ? 200 : 80, sparkline: { enabled: !isMain } },
            colors: ['#6c757d', '#ffc107', '#28a745'],
            labels: ['Untouched', 'Unreached', 'Reached'],
            legend: { show: false },
            dataLabels: { enabled: false },
            plotOptions: { pie: { donut: { size: '75%' } } }
        };
        const chart = new ApexCharts(el, options);
        chart.render();
        return chart;
    }
}
registry.category("actions").add("CZDboard.main", CZDboard);