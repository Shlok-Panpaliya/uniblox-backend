import json
import os
import traceback
import uuid
from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient, ReadPreference, UpdateOne, WriteConcern
from bson import ObjectId
import certifi

app = Flask(__name__)

# load enviorenment variables.
load_dotenv()

# for SSL certificates.
ca = certifi.where()

# create client for mongo connection.
client = MongoClient()

# Mongo url for connection
Mongo_Url = os.getenv("MONGO_PRODUCTION")
print(Mongo_Url, "check mongo url")

# connect using the connection string
mongo_client = MongoClient(
    "mongodb+srv://myAtlasDBUser:shlokp762@myatlasclusteredu.js7wlsy.mongodb.net/", tlsCAFile=ca)

print(Mongo_Url)

# define database and collections.
database = mongo_client["uniblox"]

# define required collection in mongo.
users = database["users"]
products = database["products"]
orders = database["orders"]
coupons = database['coupons']

# for cross origin access.
CORS(app, origins=['*'], methods=['GET', 'POST'],
     allow_headers=['Content-Type'])

# API for getting user details.


@app.route('/api/get-user-data', methods=['GET'])
def get_user_details():
    try:
        # get user_id from arguments of request.
        user_id = request.args.get('user_id')

        print(user_id, "deubgging console", ObjectId(user_id))

        # get user data.
        cursor = users.aggregate([
            {"$match": {"_id": ObjectId(user_id)}},
            {
                "$project": {
                    '_id': {'$toString': '$_id'},
                    'name': 1,
                    'email': 1,
                    'phone': 1,
                    'itemsInCart': {
                        "$map": {
                            "input": "$itemsInCart",
                            "in": {
                                # Convert ObjectId to string
                                "_id": {'$toString': "$$this._id"},
                                "name": "$$this.name",
                                "images": "$$this.images",
                                "price": "$$this.price",
                                "stock": "$$this.stock",
                            }
                        }
                    },
                    'ordersPlaced': {
                        "$map": {
                            "input": "$ordersPlaced",
                            "in": {
                                # Convert ObjectId to string
                                "_id": {'$toString': "$$this._id"},
                            }
                        }
                    },
                    'coupons': 1
                }
            }
        ])

        data = list(cursor)

        # console for debugging
        print(data, "user response")

        # if user data is found return the user else throw error.
        if len(data) > 0:
            return {
                "status_code": 200,
                "data": data[0]
            }
        else:
            return {
                "status_code": 404,
                "data": "No user found."
            }

    except Exception as e:
        # Print the traceback information of the error.
        traceback_info = traceback.format_exc()
        print("Traceback Information:", traceback_info)

        return {
            'status_code': 500,
            'data': "Error while fetching user data."
        }

# API for adding items to cart of a user identified by their User ID.


@app.route('/api/add-items-to-cart', methods=['POST'])
def add_items_to_cart():
    try:
        # get data passde in body of the request.
        data = request.get_json()

        print(data, "chcek data")

        # get product_id of the item.
        product_id = data['product_id']

        # get user_id of the user.
        user_id = data['user_id']

        # get product from the products collection.
        product = products.find_one({"_id": ObjectId(product_id)})

        # update stock of the item.
        # products.update_one(
        #     {"_id": ObjectId(product_id)},
        #     {"$inc": {"stock": -1}}
        # )

        # add product to the cart of the user.
        res = users.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"itemsInCart": product}}
        )

        # if product is added to cart successfully return success else return error.
        if res.acknowledged:
            return {
                "status_code": 200,
                "message": "Item added to cart successfully."
            }
        else:
            return {
                "status_code": 500,
                "message": "Error while adding item to cart."
            }

    except:
        # Print the traceback information of the error.
        traceback_info = traceback.format_exc()
        print("Traceback Information:", traceback_info)

        return {
            'status_code': 500,
            'data': "Error while adding items to cart."
        }

# API for getting all products.


@app.route('/api/get-all-products', methods=['GET'])
def get_all_products():
    try:
        # check if available is passed in arguments so only items in stocks are returned.
        available = request.args.get('available')

        # mongo pipeline.
        pipeline = []

        # If available if true then only return items in stock.
        if available == "Yes":
            # return items which are in stock.
            pipeline.append({
                "$match": {
                    "stock": {"$gt": 0}
                }
            })
        else:
            # return all items.
            pipeline.append({
                "$match": {}
            })

        # remove _id from response for json parsing.
        pipeline.append({
            "$project": {
                '_id': {'$toString': '$_id'},
                'name': 1,
                'price': 1,
                'stock': 1,
                'images': 1,
            }
        })

        # query to get all products.
        cursor = products.aggregate(pipeline)

        # response to be returned.
        data = list(cursor)

        print(data, "data")

        # if products are found return the products else return no products found.
        if len(data) > 0:
            # return the response.
            return {
                "status_code": 200,
                "data": data
            }

        else:
            return {
                "status_code": 404,
                "data": "No products found."
            }

    except Exception as e:
        # Print the traceback information of the error.
        traceback_info = traceback.format_exc()
        print("Traceback Information:", traceback_info)

        return {
            'status_code': 500,
            'data': "Error while fetching products data."
        }


@app.route('/api/generate-coupon-code', methods=['GET'])
def generate_coupon_code():
    try:
        # Generate UUID4 and format as a string
        coupon = str(uuid.uuid4()).upper().replace('-', '')[:8]
        
        # Insert coupon code in coupons collection.
        res = coupons.insert_one({
            "coupon_code": coupon,
            "discount": 10,
            "is_active": True
        })
        
        if res.acknowledged:
            return {
                "status_code": 200,
                "data": coupon
            }
        
        return {
            "status_code": 500,
            "message": "Error while generating coupon code."
        }    
        
    except:
        # Print the traceback information of the error.
        traceback_info = traceback.format_exc()
        print("Traceback Information:", traceback_info)

        return {
            'status_code': 500,
            'data': "Error while generating coupon code."
        }


@app.route('/api/complete-order', methods=['POST'])
def complete_order():
    try:
        # get data passde in body of the request.
        data = request.get_json()

        print(data, "chcek data")

        # get user_id of the user.
        user_id = data['user_id']
        
        # chcek coupon code is applied.
        coupon_code = data['coupon_code']

        # if user_id is None return.
        if user_id == None:
            return {
                "status_code": 500,
                "message": "User ID is required."
            }

        # get user from the users collection.
        user = users.find_one({"_id": ObjectId(user_id)})

        # if user is None return.
        if user == None:
            return {
                "status_code": 500,
                "message": "User not found."
            }

        # get items from the cart of the user.
        items_in_cart = user['itemsInCart']

        # store object ids of all items.
        item_ids = [item['_id'] for item in items_in_cart]

        # create bulk operations for updating stock of the items.
        bulk_operations = []
        
        # calculate total price of the order.
        total_price = 0
        for item in items_in_cart:
            total_price += item['price']
        
        # if coupon code is applied then apply discount.
        if coupon_code != None:
            # get coupon from the coupons collection.
            coupon = coupons.find_one({"coupon_code": coupon_code})
            
            # if coupon is active then apply discount.
            if coupon != None and coupon['is_active']:
                total_price = total_price - (total_price * coupon['discount'] / 100)

        # for each item in cart create a bulk operation to update stock.
        for obj_id in item_ids:
            bulk_operations.append(
                UpdateOne(
                    {"_id": obj_id},
                    {"$inc": {"stock": -1}}
                )
            )

        # define callback for transaction.
        def complete_order_transaction_callback(session):
            # define collections to be used.
            orders = session.client.uniblox.orders
            users = session.client.uniblox.users
            products = session.client.uniblox.products

            # insert order in orders collection.
            res = orders.insert_one({
                "user_id": user_id,
                "items": items_in_cart,
                "total_price": total_price,
                "status": "Pending",
            })

            # update items in cart and order in users collection.
            users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"itemsInCart": []},
                    "$push": {"ordersPlaced": {"orderId": res.inserted_id, "totalPrice": total_price}}},
                upsert=False
            )

            # update stock of the items in products collection.
            products.bulk_write(bulk_operations)

        # create a transaction for placing order which will be atomic.
        wc_majority = WriteConcern("majority", wtimeout=1000)

        # start transaction.
        with mongo_client.start_session() as session:
            # Step 3: Use with_transaction to start a transaction, execute the callback, and commit (or abort on error).
            session.with_transaction(
                complete_order_transaction_callback,
                write_concern=wc_majority,
                read_preference=ReadPreference.PRIMARY,
            )
            
            return {
                "status_code": 200,
                "message": "Order placed successfully."
            }

    except:
        # Print the traceback information of the error.
        traceback_info = traceback.format_exc()
        print("Traceback Information:", traceback_info)

        return {
            'status_code': 500,
            'data': "Error while completing order."
        }


if __name__ == "__main__":
    app.run(debug=True)
