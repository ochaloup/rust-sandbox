// use borsh::{BorshDeserialize, BorshSerialize};

fn main() {
    let hello_world = "Hello, world! Česko";
    println!("Output: '{}'", hello_world);
    
    let mut hello_world_slice: [u8;30] = [0; 30];
    hello_world_slice[0..hello_world.len()].copy_from_slice(hello_world.as_bytes());    
    println!(
        "Output slice: '{:?}'/'{}'",
        hello_world_slice, std::str::from_utf8(&hello_world_slice).unwrap()
    );
}
