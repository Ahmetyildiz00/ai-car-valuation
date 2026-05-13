// Custom Cypress commands.

Cypress.Commands.add("login", (email, password) => {
  cy.request("POST", `${Cypress.env("apiUrl")}/auth/login`, { email, password }).then((res) => {
    window.localStorage.setItem("access_token", res.body.access_token);
  });
});

Cypress.Commands.add("clearAuth", () => {
  window.localStorage.removeItem("access_token");
  window.localStorage.removeItem("anon_client_id");
});
