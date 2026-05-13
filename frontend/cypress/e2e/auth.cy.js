describe("Auth flow", () => {
  beforeEach(() => {
    cy.clearAuth();
  });

  it("shows the login form", () => {
    cy.visit("/login");
    cy.get('input[type="email"]').should("be.visible");
    cy.get('input[type="password"]').should("be.visible");
    cy.contains("button", /Giriş/i).should("be.visible");
  });

  it("redirects unauthenticated users away from /dashboard", () => {
    cy.visit("/dashboard");
    cy.location("pathname").should("eq", "/login");
  });
});
