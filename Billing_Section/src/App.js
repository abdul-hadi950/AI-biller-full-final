import "./App.css";
import { Scrollbars } from "react-custom-scrollbars-2";
import Items from "./components/items";
import Header from "./components/Header";
import { useEffect, useState } from "react";
import QRCode from "react-qr-code";

import io from "socket.io-client";

function App() {
  const [items, setItems] = useState([]); // array of items from database
  const [socketInstance, setSocketInstance] = useState("");
  const [itemsCount, setItemsCount] = useState(0);
  const [totalAmount, setTotalAmount] = useState(0);
  const [checkoutClicked, setCheckoutClicked] = useState(false);

  useEffect(() => {
    const socket = io("http://localhost:5000");

    socket.on("connect", (data) => {
      console.log(data);
    });

    setSocketInstance(socket);

    socket.on("disconnect", (data) => {
      console.log(data);
    });

    socket.on("data", (data) => {
      setItemsCount(data.results.length);
      setItems(data.results);
    });

    // Clean up socket connection on unmount
    return () => {
      socket.disconnect();
    };
  }, []);

  // if any changes occurs to items (even in case of addition/reduction of quantities)
  useEffect(() => {
    setTotalAmount(
      items.reduce((acc, item) => {
        return acc + item.price * item.quantity;
      }, 0)
    );
  }, [items]);

  // for clear cart button
  const handleDeleteAll = () => {
    socketInstance.emit("delete_all");
    setItemsCount(0);
  };

  // for checkout button
  const handleCheckout = () => {
    setCheckoutClicked(true);
    setTimeout(() => {
      handleDeleteAll();
      setCheckoutClicked(false);
      setItemsCount(0);
    }, 5000);
  };

  // Page consists of mainly three sections: Header, Scrollbars Section, Clearcart & Checkout btn section
  // Last section is displayed only in case of itemsCount != 0
  // Content of Scrollbars section depends on itemsCount == 0 and itemsCount != 0
  return (
    <>
      <Header cartItems={itemsCount} />

      {!checkoutClicked ? (
        <section className="main-cart-section">
          <div className="cart-items">
            <div className="cart-items-container">
              <Scrollbars>
                {itemsCount === 0 ? (
                  <h1 className="place-items">Place the items</h1>
                ) : (
                  items.map((item) => (
                    <Items
                      key={item.product_id}
                      item_details={item}
                      socket={socketInstance}
                    />
                  ))
                )}
              </Scrollbars>
            </div>
          </div>
        </section>
      ) : (
        <section className="main-cart-section">
          <h1>Shopping Cart Checkout Page</h1>
          <p className="total-items">
            Pay<span className="total-items-count"> {totalAmount}</span> Rs and
            enjoy the day.
          </p>
          <div className="cart-items">
            <div className="cart-items-container">
              <div className="qr">
                <h2>Scan the Code to pay</h2>
                <QRCode
                  value={`upi://pay?pa=UPI_ID&pn=YOUR_NAME&tn=payment&am=${totalAmount}&cu=INR`}
                />
                <h2>Total Amount : {totalAmount}₹ </h2>
              </div>
            </div>
          </div>
        </section>
      )}

      {itemsCount !== 0 && !checkoutClicked && (
        <section className="main-cart-section">
          <div className="cart-total">
            <h3>
              Cart Total : <span>{totalAmount} ₹</span>
            </h3>
            <button className="checkout-btn" onClick={handleCheckout}>
              Checkout
            </button>
            <button className="clear-cart-btn" onClick={handleDeleteAll}>
              Clear Cart
            </button>
          </div>
        </section>
      )}
    </>
  );
}

export default App;
