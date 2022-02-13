fn main() {
    let my_tup = (1,2,"33");
    let (_,_,z) = my_tup;
    println!("Z value is {}", z);

    let x: (i32, f64, u8) = (500, 6.4, 1);
    let _five_hundred = x.0;
    let _six_point_four = x.1;
    let one = x.2;
    println!("tuples: {:?}, one: {}", x, one);

    let a = [1, 2, 3, 4, 5];
    let a = [3;5];
    println!("array: {:?}", a);
}