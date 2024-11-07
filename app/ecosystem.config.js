module.exports = {
    apps: [
        {
            name: 'agent-api',
            script: 'uvicorn main:app --host 0.0.0.0',
            args: '',
            instances: 1,
            autorestart: true,
            watch: false,
            max_memory_restart: '1G',
        }
    ]
};