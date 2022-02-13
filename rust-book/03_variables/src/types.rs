fn main() {
    let my_tup = (1,2,"33");
    let (_,_,z) = my_tup;
    println!("Z value is {}", z);

    let x: (i32, f64, u8) = (500, 6.4, 1);
    let _five_hundred = x.0;  // => accesing tuple at index 0
    let _six_point_four = x.1;  // => accesing tuple at index 1
    let one = x.2;
    println!("tuples: {:?}, one: {}", x, one);

    let _a = [1, 2, 3, 4, 5];  // => underscore prefix defines that is expected the variable won't be used
    let a = [3;5];  // => [3,3,3,3,3]
    // => {:?} needed to pring when trait Display is not implemented
    // => {:#?} means pretty print
    println!("item0: {}", a[0]);
    println!("array: {:?}", a);
    println!("array: {:#?}", a);
}