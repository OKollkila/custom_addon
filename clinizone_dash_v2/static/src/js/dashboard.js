/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc"; 
import { Component, useState, onWillStart, onMounted, useEffect } from "@odoo/owl";

export class CZDboardV2 extends Component {
    // تم تغيير الـ Template Name ليتوافق مع الموديول الجديد
    static template = "clinizone_dash_v2.MainTemplate";
    static props = { "*": true }; 

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            showFilters: true,
            selectedDept: null, 
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
            activeSalesTab: 'all',
        });

        onWillStart(async () => {
            await loadJS("https://cdn.jsdelivr.net/npm/apexcharts");
        });

        useEffect(() => {
            if (window.ApexCharts && !this.state.loading) {
                const timer = setTimeout(() => {
                    if (this.state.selectedDept) {
                        this._renderSourceCharts();
                    } else if (this.state.hasData) {
                        this._renderDepartmentCharts();
                    }
                }, 250);
                return () => clearTimeout(timer);
            }
        }, () => [this.state.stats, this.state.hasData, this.state.selectedDept]);

        onMounted(async () => {
            await this._loadInitialFilters();
        });
    }

    _getFormattedDate(date) { return date.toISOString().split('T')[0]; }

    getSafeId(prefix, name) {
        if (!name) return prefix + '_unknown';
        return prefix + '_' + name.toString().replace(/[^a-z0-9]/gi, '_').toLowerCase();
    }

    _getColorForPercentage(pct) {
        const r = Math.floor(233 - (pct * 1.6)); 
        const g = Math.floor(102 + (pct * 0.6)); 
        const b = Math.floor(102 - (pct * 0.1));
        return `rgb(${r},${g},${b})`;
    }

    openDetails(dept) {
        this.state.selectedDept = dept;
        const scrollEl = document.querySelector('.o_action_manager');
        if (scrollEl) scrollEl.scrollTop = 0;
    }

    backToMain() {
        this.state.selectedDept = null;
    }

   _renderSourceCharts() {
        if (!this.state.selectedDept) return;
        const dept = this.state.selectedDept;

        // 1. شارت الإجمالي للإدارة (Main Total)
        const mainChartId = 'dept_main_total_chart';
        const mainContainer = document.getElementById(mainChartId);
        if (mainContainer) {
            mainContainer.innerHTML = '';
            const md = dept.data_points;
            const maxVal = Math.max(md.untouched, md.unreached, md.reached, 1);
            const scaledCR = (dept.calculated_cr / 100) * maxVal;

            new ApexCharts(mainContainer, {
                series: [{ name: 'Total', data: [md.untouched, md.unreached, md.reached, md.booked, scaledCR] }],
                chart: { type: 'bar', height: 300, toolbar: { show: false } },
                plotOptions: { bar: { distributed: true, borderRadius: 8, dataLabels: { position: 'top' } } },
                colors: ['#7163AD', '#5BC0DE', '#00A09D', '#45A760', '#E96666'],
                dataLabels: {
                    enabled: true,
                    offsetY: -25,
                    style: { fontSize: '12px', fontWeight: 'bold', colors: ["#333"] },
                    formatter: (val, opts) => {
                        if (opts.dataPointIndex === 4) return dept.calculated_cr + "%";
                        const total = md.untouched + md.unreached + md.reached;
                        const p = total > 0 ? ((val/total)*100).toFixed(0) : 0;
                        return val + " (" + p + "%)";
                    }
                },
                xaxis: { categories: ['Untouched', 'Unreached', 'Reached', 'Booked', 'Overall CR%'] },
                yaxis: { show: false },
                legend: { show: false }
            }).render();
        }

        // 2. شارتات المصادر (Lead Sources)
        dept.sources.forEach(source => {
            const chartId = this.getSafeId('source_chart', source.name);
            const container = document.getElementById(chartId);
            if (!container) return;
            container.innerHTML = '';

            const crVal = parseFloat(source.cr_display || 0);
            const sTotal = (source.untouched || 0) + (source.unreached || 0) + (source.reached || 0);
            const maxS = Math.max(source.untouched || 0, source.unreached || 0, source.reached || 0, 1);
            const scaledSCR = (crVal / 100) * maxS;

            new ApexCharts(container, {
                series: [{ name: 'Source Stats', data: [source.untouched || 0, source.unreached || 0, source.reached || 0, source.booked || 0, scaledSCR] }],
                chart: { type: 'bar', height: 250, toolbar: { show: false } },
                plotOptions: { bar: { distributed: true, borderRadius: 6, dataLabels: { position: 'top' } } },
                colors: ['#7163AD', '#5BC0DE', '#00A09D', '#45A760', '#E96666'],
                dataLabels: {
                    enabled: true,
                    offsetY: -20,
                    style: { fontSize: '10px', fontWeight: 'bold' },
                    formatter: (val, opts) => {
                        if (opts.dataPointIndex === 4) return crVal + "%";
                        const p = sTotal > 0 ? ((val/sTotal)*100).toFixed(0) : 0;
                        return val + " (" + p + "%)";
                    }
                },
                xaxis: { categories: ['Untouched', 'Unreached', 'Reached', 'Booked', 'CR%'] },
                yaxis: { show: false },
                legend: { show: false }
            }).render();
        });
    }

    async onApplyFilters() {
        this.state.loading = true;
        this.state.hasData = false;
        this.state.stats = [];

        const params = {
            city_ids: this.state.selected.city_ids.length > 0 ? this.state.selected.city_ids : null,
            company_ids: this.state.selected.company_ids.length > 0 ? this.state.selected.company_ids : null,
            branch_ids: this.state.selected.branch_ids.length > 0 ? this.state.selected.branch_ids : null,
            date_from: this.state.selected.date_from,
            date_to: this.state.selected.date_to
        };

        try {
            const [crmResponse, salesResponse] = await Promise.all([
                rpc("/web/czdboard/v2/get_crm_stats", params),
                rpc("/web/czdboard/v2/get_sales_stats", params)
            ]);

            const processDept = (dept, type) => {
                let u = 0, ur = 0, r = 0, b = 0;
                
                const processedSources = (dept.sources || []).map(s => {
                    const sourceReached = s.reached || 0;
                    const sourceBooked = s.booked || 0;
                    return {
                        ...s,
                        cr_display: sourceReached > 0 ? ((sourceBooked / sourceReached) * 100).toFixed(1) : "0"
                    };
                });

                if (dept.sources) {
                    dept.sources.forEach(s => {
                        u += (s.untouched || 0);
                        ur += (s.unreached || 0);
                        r += (s.reached || 0);
                        b += (s.booked || 0);
                    });
                }
                const total = u + ur + r;
                return {
                    ...dept,
                    sources: processedSources,
                    display_name: dept.name,
                    dashboard_type: type,
                    unique_id: `${type}_${dept.name.replace(/\s+/g, '_')}`,
                    total_count: dept.total_count || total,
                    calculated_cr: r > 0 ? parseFloat(((b / r) * 100).toFixed(1)) : 0,
                    data_points: { 
                        untouched: u, unreached: ur, reached: r, booked: b,
                        u_perc: total > 0 ? ((u/total)*100).toFixed(0) : 0,
                        ur_perc: total > 0 ? ((ur/total)*100).toFixed(0) : 0,
                        r_perc: total > 0 ? ((r/total)*100).toFixed(0) : 0
                    }
                };
            };

            const crmData = (crmResponse?.data || []).map(d => processDept(d, 'CRM'));
            const salesRaw = Array.isArray(salesResponse) ? salesResponse : (salesResponse?.data || []);
            const salesData = salesRaw.filter(d => d.id !== 'all' && d.name !== 'Total Sales').map(d => processDept(d, 'SALES'));

            this.state.stats = [...crmData, ...salesData];
            this.state.hasData = this.state.stats.length > 0;
        } catch (error) { 
            console.error(error); 
        } finally { 
            this.state.loading = false; 
        }
    }

    _renderDepartmentCharts() {
        this.state.stats.forEach(dept => {
            const chartId = this.getSafeId('dept_chart', dept.unique_id);
            const container = document.getElementById(chartId);
            if (!container) return;
            container.innerHTML = '';

            const { untouched, unreached, reached, u_perc, ur_perc, r_perc } = dept.data_points;
            const crValue = dept.calculated_cr;
            const maxLeads = Math.max(untouched, unreached, reached, 1);
            const adjustedCR = (crValue / 100) * maxLeads;

            const options = {
                series: [{ name: 'Performance', data: [untouched, unreached, reached, adjustedCR] }],
                chart: { type: 'bar', height: 350, toolbar: { show: false } },
                plotOptions: {
                    bar: {
                        distributed: true,
                        borderRadius: 6,
                        columnWidth: '80%',
                        dataLabels: { position: 'center' }
                    }
                },
                colors: ['#7163AD', '#5BC0DE', '#00A09D', this._getColorForPercentage(crValue)],
                dataLabels: {
                    enabled: true,
                    style: { fontSize: '15px', fontWeight: 'bold', colors: ['#fff'] },
                    formatter: function (val, opts) {
                        const idx = opts.dataPointIndex;
                        if (idx === 0) return [untouched, u_perc + "%"];
                        if (idx === 1) return [unreached, ur_perc + "%"];
                        if (idx === 2) return [reached, r_perc + "%"];
                        return crValue + "%";
                    }
                },
                xaxis: { 
                    categories: ['Untouched', 'Unreached', 'Reached', 'CR %'],
                    labels: { style: { fontWeight: 'bold' } }
                },
                yaxis: { show: false },
                tooltip: {
                    y: {
                        formatter: (val, opts) => {
                            if (opts.dataPointIndex === 3) return crValue + "%";
                            return val + " Leads";
                        }
                    }
                },
                legend: { show: false }
            };

            new ApexCharts(container, options).render();
        });
    }

    async _loadInitialFilters() {
        try {
            const result = await rpc("/web/czdboard/v2/filters", {});
            if (result && result.status === "ok") {
                this.state.filterOptions.cities = result.data.cities;
                await this._updateCompanies();
            }
        } catch (e) {}
    }

    async _updateCompanies() {
        const res = await rpc("/web/czdboard/v2/get_companies_by_cities", { 
            city_ids: this.state.selected.city_ids.length > 0 ? this.state.selected.city_ids : null 
        });
        this.state.filterOptions.companies = res.data || [];
    }

    async _updateBranches() {
        const res = await rpc("/web/czdboard/v2/get_branches_refined", { 
            city_ids: this.state.selected.city_ids.length > 0 ? this.state.selected.city_ids : null,
            company_ids: this.state.selected.company_ids.length > 0 ? this.state.selected.company_ids : null
        });
        this.state.filterOptions.branches = res.data || [];
    }

    toggleItem(fieldName, id, ev) {
        if (ev.target.checked) {
            if (!this.state.selected[fieldName].includes(id)) this.state.selected[fieldName].push(id);
        } else {
            const index = this.state.selected[fieldName].indexOf(id);
            if (index > -1) this.state.selected[fieldName].splice(index, 1);
        }
        if (fieldName === 'city_ids') { this._updateCompanies(); this._updateBranches(); }
        if (fieldName === 'company_ids') this._updateBranches();
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

    toggleFilters() {
        this.state.showFilters = !this.state.showFilters;
    }
}

// تم تغيير اسم التاج ليكون متميزاً للنسخة الجديدة
registry.category("actions").add("clinizone_dash_v2.main", CZDboardV2);