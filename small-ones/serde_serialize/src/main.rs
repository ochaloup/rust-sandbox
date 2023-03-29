use serde::{Serialize, Deserialize};

#[repr(u8)]
#[derive(Debug, Deserialize, Serialize)]
enum AnEnum {
    A(i32),
    B(i32),
    C,
}

fn main() {
    println!("Hello, world!");
    let a = AnEnum::C;

    // let mut file = File::create("foo.txt").expect("open file");
    // file.write_all(a.into()).expect("write data");
    let encoded: Vec<u8> = bincode::serialize(&a).unwrap();
    println!("{:?}", encoded);
}
