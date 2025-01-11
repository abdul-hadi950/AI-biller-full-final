import React, { useEffect, useState } from "react";
import "../App.css";

function Items({ item_details, socket }) {
  const [itemQuantity, setItemQuantity] = useState(item_details.quantity);

  const decrement = () => {
    setItemQuantity(itemQuantity - 1);
  };
  const increment = () => {
    setItemQuantity(itemQuantity + 1);
  };

  // for deletion of single product
  const handleDelete = () => {
    socket.emit("delete_product", {
      Id: item_details.product_id,
    });
  };

  // occurs when there any change in itemQuantity
  useEffect(() => {
    if (itemQuantity === 0) {
      handleDelete();
    } else {
      socket.emit("change_quantity", {
        Id: item_details.product_id,
        Quantity: itemQuantity,
      });
    }
  }, [itemQuantity]);

  return (
    <>
      <div className="items-info">
        <div className="title">
          <h2>{item_details.product_name}</h2>
        </div>

        {item_details.product_name !== "Lemon" ? (
          <div className="add-minus-quantity">
            <i className="fas fa-minus minus" onClick={decrement}></i>
            <input type="text" placeholder={itemQuantity} disabled />
            <i className="fas fa-plus add" onClick={increment}></i>
          </div>
        ) : (
          <div className="add-minus-quantity">
            <input type="text" placeholder={itemQuantity} disabled />
          </div>
        )}

        <div className="price">
          <h3>{Math.round(itemQuantity * item_details.price * 100) / 100}</h3>
        </div>

        <div className="remove-item">
          <i className="fas fa-trash-alt remove" onClick={handleDelete}></i>
        </div>
      </div>

      <hr />
    </>
  );
}

export default Items;
