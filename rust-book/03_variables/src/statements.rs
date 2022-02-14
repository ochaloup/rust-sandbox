
fn typeid<T: std::any::Any>(_: &T) {
    println!("{:?}", std::any::TypeId::of::<T>());
}


fn main() {
    // => expression do not(!) end with semicolon, then they return a value
    let y = {
        let x = 3;
        x + 1
    };
    // => statements end(!) with semicolon, then they return no value
    let z = {
        let x = 3;
        x + 1;
    };

    typeid(&z);
    println!("The value of y is: {}, the value of z is {:?}, plus one is: {}", y, z, plus_one(y));
}

fn plus_one(x: i64) -> i64 {
    x + 1
}

