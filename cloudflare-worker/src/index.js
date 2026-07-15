export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(triggerWorkflow(env));
  },

  // Permite probar manualmente visitando la URL del Worker (GET/POST).
  async fetch(request, env, ctx) {
    await triggerWorkflow(env);
    return new Response("Workflow dispatch enviado.");
  },
};

async function triggerWorkflow(env) {
  const url =
    `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}` +
    `/actions/workflows/${env.GITHUB_WORKFLOW_FILE}/dispatches`;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "ticket-monitor-cron-worker",
    },
    body: JSON.stringify({ ref: env.GITHUB_REF || "main" }),
  });

  if (!resp.ok) {
    const body = await resp.text();
    console.error(`GitHub dispatch failed: ${resp.status} ${body}`);
    throw new Error(`GitHub dispatch failed: ${resp.status}`);
  }

  console.log("Workflow dispatch enviado correctamente.");
}
