describe("Landing page", () => {
  beforeEach(() => {
    cy.clearAuth();
    cy.visit("/");
  });

  it("renders hero and upload card", () => {
    cy.contains("Carval").should("be.visible");
    cy.contains("Aracınızın Gerçek").should("be.visible");
    cy.contains("Giriş Yap").should("be.visible");
    cy.contains("Üye Ol").should("be.visible");
  });

  it("disables the evaluate button until an image or URL is provided", () => {
    cy.contains("button", "Değeri Tahmin Et").should("be.disabled");
    cy.get('input[type="url"]').type("https://example.com/car.jpg");
    cy.contains("button", "Değeri Tahmin Et").should("not.be.disabled");
  });

  it("navigates to /valuation when evaluate is clicked", () => {
    cy.get('input[type="url"]').type("https://example.com/car.jpg");
    cy.contains("button", "Değeri Tahmin Et").click();
    cy.location("pathname").should("eq", "/valuation");
  });
});
