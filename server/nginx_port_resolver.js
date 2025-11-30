// nginx njs script to resolve project port via API call
// Calls Django API to get the port for a project ID

function resolveProxyUrl(s) {
    var subdomain = s.variables.id;
    
    // If subdomain is "api", route to Django
    if (subdomain === "api") {
        return "http://127.0.0.1:8000";
    }
    
    // For UUID subdomains, call Django API to get port
    // This ensures we use the exact same port calculation as the server
    try {
        var req = ngx.fetch('http://127.0.0.1:8000/api/jobs/port/' + subdomain, {
            method: 'GET',
            headers: {
                'Host': 'api.projectengine.dev'
            }
        });
        
        if (req.status === 200) {
            var data = req.json();
            return data.url || "http://127.0.0.1:" + data.port;
        }
    } catch (e) {
        // Fallback: calculate port using simple hash (may not match exactly)
        var hash = 0;
        for (var i = 0; i < subdomain.length; i++) {
            hash = ((hash << 5) - hash) + subdomain.charCodeAt(i);
            hash = hash & hash;
        }
        var port = 30000 + (Math.abs(hash) % 19000);
        return "http://127.0.0.1:" + port;
    }
    
    // Default fallback
    return "http://127.0.0.1:30000";
}

export default { resolveProxyUrl };

