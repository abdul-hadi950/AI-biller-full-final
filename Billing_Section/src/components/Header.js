import React from "react";

function Header({ cartItems }) {
  return (
    <div>
      <header>
        <div className="heading">
          <h3>A I Biller</h3>
        </div>
      </header>

      <section className="main-cart-section">
        <h1>Shopping Cart</h1>
        <p className="total-items">
          You have <span className="total-items-count">{cartItems}</span> items
          in shopping cart
        </p>
      </section>
    </div>
  );
}

export default Header;
