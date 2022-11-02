use core;

// How to work with slices and how to copy item at particular place in array
fn main() {
    // array definition
    let mut numbers1:[u8;5] = [1, 2, 3, 4, 5];
    // printing slice of all members
    println!("numbers1: {:?}", &numbers1[..]);

    // [u8] definition
    let new_number:[u8;1] = [128];
    // using Copy trait to place the new content into array
    numbers1[..1].copy_from_slice(&new_number);
    println!("numbers1: {:?}", &numbers1);

    // array definition
    let mut numbers2: [u8; 5] = core::array::from_fn(|i| i as u8 + 1);
    println!("numbers2: {:?}", numbers2);

    use std::slice;
    // getting slice of the first member of the array; borrowing mutable reference of the slice
    let first_number = slice::from_mut(&mut numbers2[0]);
    // changing the mutable slice with a number with Clone trait
    first_number.clone_from_slice(&new_number);
    println!("numbers2: {:?}", &numbers2);
}
