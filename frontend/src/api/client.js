/* UniGPU — API Client */

const BASE = 'http://localhost:8000';

function getToken() {
    return localStorage.getItem('token');
}

function authHeaders() {
    const t = getToken();
    return t ? { Authorization: `Bearer ${t}` } : {};
}

async function request(method, path, { body, files } = {}) {
    const opts = { method, headers: { ...authHeaders() } };

    if (files) {
        const fd = new FormData();
        for (const [k, v] of Object.entries(files)) fd.append(k, v);
        opts.body = fd;
    } else if (body) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
    }

    const res = await fetch(`${BASE}${path}`, opts);
    const data = res.headers.get('content-type')?.includes('json')
        ? await res.json()
        : await res.text();

    if (!res.ok) {
        throw { status: res.status, detail: data?.detail || data };
    }
    return data;
}

const api = {
    // Auth
    register: (d) => request('POST', '/auth/register', { body: d }),
    login: (d) => request('POST', '/auth/login', { body: d }),

    // GPUs
    listGPUs: () => request('GET', '/gpus/'),
    availableGPUs: (minVram) => request('GET', `/gpus/available?min_vram=${minVram || 0}`),
    registerGPU: (d) => request('POST', '/gpus/register', { body: d }),
    updateGPU: (id, d) => request('PATCH', `/gpus/${id}/status`, { body: d }),

    // Jobs
    submitJob: (script, requirements) => {
        const files = { script };
        if (requirements) files.requirements = requirements;
        return request('POST', '/jobs/submit', { files });
    },
    listJobs: () => request('GET', '/jobs/'),
    getJob: (id) => request('GET', `/jobs/${id}`),
    getJobLogs: (id) => request('GET', `/jobs/${id}/logs`),

    // Wallet
    getWallet: () => request('GET', '/wallet/'),
    topUp: (amount) => request('POST', '/wallet/topup', { body: { amount } }),
    getTransactions: () => request('GET', '/wallet/transactions'),

    // Admin
    adminStats: () => request('GET', '/admin/stats'),
    adminGPUs: () => request('GET', '/admin/gpus'),
    adminJobs: () => request('GET', '/admin/jobs'),
    adminUsers: () => request('GET', '/admin/users'),
};

export default api;
