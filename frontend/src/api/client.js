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

    // Handle 204 No Content (e.g. DELETE responses)
    if (res.status === 204) return null;

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
    submitJob: (script, requirements, gpuId) => {
        const files = { script };
        if (requirements) files.requirements = requirements;
        // gpu_id is sent as a form field alongside the files
        const opts = { files };
        if (gpuId) {
            // We need to add gpu_id to the FormData manually
            return (async () => {
                const fd = new FormData();
                fd.append('script', script);
                if (requirements) fd.append('requirements', requirements);
                fd.append('gpu_id', gpuId);
                const res = await fetch(`${BASE}/jobs/submit`, {
                    method: 'POST',
                    headers: { ...authHeaders() },
                    body: fd,
                });
                const data = await res.json();
                if (!res.ok) throw { status: res.status, detail: data?.detail || data };
                return data;
            })();
        }
        return request('POST', '/jobs/submit', { files });
    },
    listJobs: () => request('GET', '/jobs/'),
    getJob: (id) => request('GET', `/jobs/${id}`),
    getJobLogs: (id) => request('GET', `/jobs/${id}/logs`),
    cancelJob: (id) => request('POST', `/jobs/${id}/cancel`),
    deleteJob: (id) => request('DELETE', `/jobs/${id}`),

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
